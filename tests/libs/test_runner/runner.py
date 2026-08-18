"""
Hardware Test Runner for FBOSS

This module provides a base class and specialized test runners for different FBOSS test types.
Each test runner subclass specifies its default configuration directories.
"""

import functools
import logging
import os
import time
import shlex
import re
import csv
import copy
import json
import tempfile
import hashlib
import shutil
import tarfile
import xml.etree.ElementTree as ET
import subprocess
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import NamedTuple

from tests.libs.device.device_ssh_helper import DeviceSCPClient, DeviceSSHClient

logger = logging.getLogger("test_runner")

# Floor (seconds) for how long a *failing* test run must occupy before
# run_test returns False.
MIN_FAILURE_DURATION_SECS = 120


def _enforce_min_failure_duration(run_test):
    """Decorator: pad a failing run out to MIN_FAILURE_DURATION_SECS.

    TE batches re-run failing tests back-to-back without re-imaging between
    them. A binary that aborts early (e.g. crashing in SetUp() in seconds)
    produces a tight fail-retry loop that hammers the DUT and floods T-Recs
    with near-instant failures. Padding any failing run to a fixed floor
    keeps the surrounding retry cadence sane. Successful runs are never
    delayed.

    Wraps the single template run_test() entry point; per-runner execution
    lives in _run_test_impl(), which is not decorated, so a run is padded at
    most once regardless of how many subclass layers it passes through.

    Deploy-only runs (FBOSS_DEPLOY_ONLY) are exempt: they stage artifacts and
    return without executing the test, so there is no fail-retry loop to pad.
    """

    @functools.wraps(run_test)
    def wrapper(self, *args, **kwargs):
        start = time.monotonic()
        success = run_test(self, *args, **kwargs)
        # Deploy-only runs stage artifacts and exit without executing the test,
        # so there's no fail-retry loop to protect against — never pad them.
        deploy_only = os.environ.get(_ENV_DEPLOY_ONLY) == _ENV_DEPLOY_ONLY_ON
        if not success and not deploy_only:
            remaining = MIN_FAILURE_DURATION_SECS - (time.monotonic() - start)
            if remaining > 0:
                logger.info(
                    "Run failed; padding to %ds floor (sleeping %.1fs)",
                    MIN_FAILURE_DURATION_SECS,
                    remaining,
                )
                time.sleep(remaining)
        return success

    return wrapper


# Map normalized model (from device DB model name) to FBOSS config codename
# Env the orchestrator (TestInstanceFboss._resolve_artifact_urls) sets.  The
# orchestrator owns *what* to use — it resolves the Nexis tarball URLs (from a
# build_id) or discovers the locally-built CMake build dir(s) — and the runner
# just consumes what it's handed for its STACK: a tarball URL (fetch + extract)
# or a local build/fboss dir (pack from binaries + repo configs).
_ENV_BUILD_ID = "FBOSS_BUILD_ID"
_STACK_FORWARDING = "forwarding"
_STACK_PLATFORM = "platform"
# Per-stack env: a Nexis CloudStack tarball URL, or a local build/fboss dir.
_ENV_TARBALL_URL = {
    _STACK_FORWARDING: "FBOSS_FORWARDING_TARBALL_URL",
    _STACK_PLATFORM: "FBOSS_PLATFORM_TARBALL_URL",
}
_ENV_LOCAL_DIR = {
    _STACK_FORWARDING: "FBOSS_FORWARDING_LOCAL_DIR",
    _STACK_PLATFORM: "FBOSS_PLATFORM_LOCAL_DIR",
}

# Per-stack share/ shipped to every runner on that stack. Forwarding tests read
# these configs (--config, --skip-known-bad-tests, --enable-production-features);
# they all live in the forwarding test tarball (package.py FORWARDING_TEST_EXTRA)
# and in the repo, so they resolve on both the Nexis and local paths. Platform
# tests read no share/ configs (run_test.py drives them by --type), so that set
# is empty. The forwarding tree is ~19 MB vs ~1 GB per test binary, so we ship
# all of it rather than a per-runner subset that can silently miss a file — only
# the binaries are worth slicing per runner (see each runner's BINARIES).
_STACK_SHARE: dict[str, tuple[str, ...]] = {
    _STACK_FORWARDING: (
        "share/hw_test_configs/",
        "share/hw_known_bad_tests/",
        "share/sai_hw_unsupported_tests/",
        "share/production_features/",
        "share/qsfp_test_configs/",
        "share/qsfp_known_bad_tests/",
        "share/qsfp_unsupported_tests/",
        "share/link_test_configs/",
        "share/link_known_bad_tests/",
        "share/hw_benchmark_tests/",
        "share/fboss2_integration_known_bad_tests/",
    ),
    _STACK_PLATFORM: (),
}

# Deploy-only mode: when set to "1" (by nhtests-run --mode deploy), run_test()
# performs setup()/_deploy_artifacts() to push this runner's slice onto the DUT,
# then returns without executing the test on the DUT. Contract is an explicit
# "1" (not mere presence) so a stray FBOSS_DEPLOY_ONLY=0/false can't silently
# skip execution.
_ENV_DEPLOY_ONLY = "FBOSS_DEPLOY_ONLY"
_ENV_DEPLOY_ONLY_ON = "1"

_FBOSS_ROOT_ON_DUT = "/opt/fboss"

# Two caches amortize two different costs (see _deploy_artifacts).
# <namespace> is the Nexis build_id, or "local-<fingerprint>" for a locally-built
# CMake tree.  The local fingerprint digests the (size, mtime_ns) of just this
# runner's uploaded sources (see _local_build_fingerprint), so a rebuilt binary
# bumps it while an in-place relink (which leaves the dir mtime untouched) is
# never masked.
#   - host extract cache (Nexis only):
#       <root>/fboss-test-cache/<namespace>/<tarball>/extracted/
#       the downloaded+extracted tarball, shared by every runner on that build_id.
#       Amortizes the expensive Nexis download+extract.  Local builds need no such
#       cache — _pack_slice reads the binaries + repo configs straight from disk.
#   - DUT marker (content-addressed):
#       /opt/fboss/.deployed/<RunnerName>.sha  holds the sha256 of the slice
#       last deployed for that runner.  If it matches the slice we're about to
#       deploy, the exact same bytes are already on the DUT — skip the SCP +
#       on-DUT extract.  No build_id; one file per runner (overwritten), so it
#       never accumulates.
def _default_host_cache_root() -> str:
    """Pick the host extract cache root for the current environment.

    On a TestEngine runner (NHTOOLS_IN_DOCKER set) the container's /tmp is
    ephemeral and consumes finite space on the k8s node. When a node's ephemeral
    storage runs low, pods are evicted. /workspace is a PVC stored outside the
    node which doesn't cause those issues.

    Dev machines don't have /workspace and instead use /tmp.
    """
    if os.environ.get("NHTOOLS_IN_DOCKER"):
        ws_root = os.environ.get("GIT_WS_ROOT", "/workspace")
        return os.path.join(ws_root, "fboss-test-cache")
    return "/tmp/fboss-test-cache"


_HOST_CACHE_ROOT = _default_host_cache_root()
_DUT_MARKER_DIR = f"{_FBOSS_ROOT_ON_DUT}/.deployed"

# Map normalized HWSKU (from device DB model name) to FBOSS config codename
# for the agent config a test passes via --config. Applies to SaiTestRunner,
# SaiAgentTestRunner and BenchmarkTestRunner; the codename is the same in
# hw_test_configs and hw_bench_configs, only the directory differs.
#
# Wedge800 naming: B/C = Broadcom/Cisco ASIC, ACT/NHP = Accton/Nexthop vendor.
#
# Sources of truth:
#   - fboss/fboss/lib/platforms/PlatformProductInfo.cpp (model -> PlatformType)
#   - fboss/fboss/oss/hw_test_configs/ and fboss/fboss/oss/hw_bench_configs/
#     (available config files)
_SAI_AGENT_CONFIG_NAME: dict[str, str] = {
    "minipack3": "montblanc",
    "nhbw800f": "wedge800bact",
    "nhcw800f": "wedge800cact",
    "nh4215f": "m4062nhp",
}

# Model → config name override for link/QSFP tests (omit when they match).
_LINK_QSFP_TEST_CONFIG_NAME: dict[str, str] = {
    "minipack3": "montblanc",
    "nh4215f": "m4062nhp",
    "nhbw800f": "wedge800bact",
    "nhcw800f": "wedge800cact",
}

# Default CREDO_SDK_VERSION in fboss/lib/phy/CredoSdkVersion.h. qsfp_bench keys
# unsupported_tests on <platform>/<phy_sdk> and matches it exactly.
_QSFP_BENCH_PHY_SDK = "credo-0.7.2"

# vendor/coldboot-sai/warmboot-sai/asic — key for run_test.py
# --skip-known-bad-tests against ./share/hw_known_bad_tests/sai*_known_bad_tests.
# Without this, ~128 known-broken tests for tomahawk5 (and the unsupported list)
# run and fail, gutting the pass rate. run_test.py auto-tries the /mono or
# /multi_switch suffix for the sai_agent file, so the same 4-tuple covers both
# SaiTestRunner and SaiAgentTestRunner.
_SAI_KNOWN_BAD_KEY: dict[str, str] = {
    "minipack3": "brcm/13.3.0.0_odp/13.3.0.0_odp/tomahawk5",
    "wedge800bact": "brcm/13.3.0.0_odp/13.3.0.0_odp/tomahawk5",
    "nhbw800f": "brcm/13.3.0.0_odp/13.3.0.0_odp/tomahawk5",
    "wedge800cact": "leaba/25.11.4210/25.11.4210/graphene202x",
    "nhcw800f": "leaba/25.11.4210/25.11.4210/graphene202x",
    "nh4010f": "brcm/13.3.0.0_odp/13.3.0.0_odp/tomahawk5",
    "nh4215f": "brcm/14.2.0.0_odp/14.2.0.0_odp/tomahawk6",
    "nh4220f": "brcm/14.2.0.0_odp/14.2.0.0_odp/tomahawk6",
}


def _sai_skip_known_bad(model: str) -> str:
    key = _SAI_KNOWN_BAD_KEY.get(model)
    return f" --skip-known-bad-tests {key}" if key else ""


def _benchmark_skip_known_bad(model: str) -> str:
    # sai_bench.materialized_JSON keys on vendor/sdk/asic (3-part), unlike the SAI
    # known-bad files which use vendor/coldboot-sai/warmboot-sai/asic. Collapse the
    # duplicated SDK segment so the benchmark platform key matches the config;
    # otherwise the lookup misses and unsupported (VOQ/Fabric/SRv6) benchmarks run.
    key = _SAI_KNOWN_BAD_KEY.get(model)
    if not key:
        return ""
    parts = key.split("/")
    if len(parts) == 4 and parts[1] == parts[2]:
        key = f"{parts[0]}/{parts[1]}/{parts[3]}"
    return f" --skip-known-bad-tests {key}"


def _normalize_model(model: str) -> str:
    """Shorten device-DB model name to FBOSS codename form, e.g. NH-4010-F -> nh4010f."""
    return model.lower().replace("-", "")


def _load_json_pairs(path: str | None) -> dict[str, str]:
    """Load a {port: peer} JSON map; {} when unset, unreadable or not a map."""
    if not path:
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            pairs = json.load(f)
    except (OSError, ValueError) as e:
        logger.warning("Could not read snake-pairs file %s: %s", path, e)
        return {}
    if not isinstance(pairs, dict):
        logger.warning("Snake-pairs file %s is not a JSON object; ignoring", path)
        return {}
    return pairs


def _cage_of(port_name: str) -> str:
    """Transceiver cage a port name belongs to: eth1/25/5 -> eth1/25."""
    parts = port_name.split("/")
    return "/".join(parts[:2]) if len(parts) >= 3 else port_name


def _neighbor_pairs(ports: list[str], pairs: dict[str, str]) -> list[tuple[str, str]]:
    """Resolve real neighbors for this pass's ports, once per cable.

    Matched by cage, not port name: `pairs` only ever names lane 1, while
    `ports` may include other lanes of the same cage. A cage with no usable
    peer contributes nothing (caller keeps its self-pair); a matched cage
    contributes only its first port, so a same-cage self-pair can't clobber it.
    """
    ports_by_cage: dict[str, list[str]] = {}
    for port in ports:
        ports_by_cage.setdefault(_cage_of(port), []).append(port)

    peer_cage = {}
    for port, peer in pairs.items():
        a, z = _cage_of(port), _cage_of(peer)
        if a != z:
            peer_cage[a] = z

    out: list[tuple[str, str]] = []
    claimed: set[str] = set()
    for cage, cage_ports in ports_by_cage.items():
        peer = peer_cage.get(cage)
        if peer is None or peer not in ports_by_cage:
            continue
        if cage in claimed or peer in claimed:
            continue
        claimed.add(cage)
        claimed.add(peer)
        out.append((cage_ports[0], ports_by_cage[peer][0]))
    return out


def _repo_dir(relative: Path) -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / relative).is_dir():
            return parent / relative
    raise FileNotFoundError(f"could not locate {relative} above {__file__}")


# Stale-state cleanup paths — must match AgentDirectoryUtil defaults
# (fboss/agent/AgentDirectoryUtil.cpp):
#   getWarmBootDir() = FLAGS_volatile_state_dir + "/warm_boot"
#                      (default /dev/shm/fboss/warm_boot)
#   agentEnsembleConfigDir() = FLAGS_persistent_state_dir + "/agent_ensemble/"
#                      (default /var/facebook/fboss/agent_ensemble/)
_WARM_BOOT_DIR = "/dev/shm/fboss/warm_boot"
_AGENT_ENSEMBLE_DIR = "/var/facebook/fboss/agent_ensemble"


_PLATFORM_MAPPING_DIR = Path(
    "fboss/lib/platform_mapping_v2/generated_platform_mappings"
)

# Link and QSFP hw test binaries have no support for profiles above 800G just yet.
_MAX_PROFILE_SPEED_MBPS = 800_000


class _PortInfo(NamedTuple):
    logical_id: int
    profile_id: int
    speed: int


class _PortTemplate(NamedTuple):
    port: dict
    vlan: dict
    vlan_port: dict
    interface: dict


def _platform_mapping_path(config_name: str) -> Path:
    """Locate a config's platform_mapping.json across both on-disk layouts.

    Descriptor-backed platforms (e.g. wedge800bact/wedge800cact) are generated
    into <vendor>/<config_name>/platform_mapping.json, while the rest keep the
    legacy flat <config_name>_platform_mapping.json. Prefer the flat file for
    backwards compat, then fall back to a vendor-directory scan mirroring
    PlatformDescriptorRegistry (fboss/lib/platforms/PlatformDescriptor.h).
    """
    base = _repo_dir(_PLATFORM_MAPPING_DIR)
    flat = base / f"{config_name}_platform_mapping.json"
    if flat.is_file():
        return flat
    nested = sorted(base.glob(f"*/{config_name}/platform_mapping.json"))
    if nested:
        return nested[0]
    raise FileNotFoundError(
        f"no platform mapping for {config_name!r}: looked for {flat} and "
        f"{base}/*/{config_name}/platform_mapping.json"
    )


def _load_platform_mapping(config_name: str) -> dict[str, _PortInfo]:
    path = _platform_mapping_path(config_name)
    with open(path, encoding="utf-8") as f:
        mapping = json.load(f)
    prof = {
        int(p["factor"]["profileID"]): p["profile"]["speed"]
        for p in mapping["platformSupportedProfiles"]
        if p["profile"]["speed"] <= _MAX_PROFILE_SPEED_MBPS
    }
    index = {}
    for entry in mapping["ports"].values():
        name = entry["mapping"]["name"]
        supported = [int(pid) for pid in entry["supportedProfiles"] if int(pid) in prof]
        if not supported:
            continue
        gmax = max(supported, key=lambda pid: prof[pid])
        index[name] = _PortInfo(entry["mapping"]["id"], gmax, prof[gmax])
    return index


class BaseHwTestRunner(ABC):
    """Base class for hardware test runners."""

    _REMOTE_CONFIG_PATH: str

    # Which FBOSS stack this runner's binaries come from.  Subclasses set this
    # to _STACK_FORWARDING or _STACK_PLATFORM; it selects the Nexis artifact
    # name and the local CMake build subdir.
    STACK: str = ""

    # Paths inside the extracted tarball that this runner needs on the DUT.
    # Trailing "/" requests a directory; everything else is treated as a single
    # file.  These are resolved against the extracted tarball root on the
    # runner host and SCP'd to the matching location under /opt/fboss/ on
    # the DUT.
    REQUIRED_PATHS: tuple[str, ...] = ()

    def __init__(self):
        self.connected = False
        self.ssh_client = None
        self.scp_client = None
        self.filter_filepath = "/home/netops/tests.conf"
        self.testlog_filepath = "/home/netops/test.log"
        self.testresult_filepath = "/home/netops/tr.xml"
        self.tc = None
        self._use_generated_config = False
        self._fboss_logging = None

    def _upload_generated_config(self, config: dict) -> None:
        with tempfile.NamedTemporaryFile("w", suffix=".materialized_JSON", delete=False) as f:
            json.dump(config, f, indent=4)
            local_path = f.name
        try:
            exit_status, output = self.scp_client.put_file(local_path, self._REMOTE_CONFIG_PATH)
        finally:
            os.unlink(local_path)
        if exit_status != 0:
            raise RuntimeError(f"Failed to upload generated config: {output}")
        self._use_generated_config = True

    @abstractmethod
    def test_args(self, model: str) -> str:
        """Returns run_test.py command arguments for this test type.

        Args:
            model: Product model (already normalized to lowercase without dashes)

        Returns:
            Command arguments as string.
            Example: "sai --config ./share/hw_test_configs/nh4010.agent.materialized_JSON"
        """

    def getenvvars(self):
        """Load environment variables into test context."""
        self.tc["dut"] = os.getenv("DUT")
        self.tc["username"] = os.getenv("DUTUSERNAME", "root")
        self.tc["password"] = os.getenv("DUTPASSWORD", "root")
        # HWSKU environment variable deprecated in favor of PRODUCT_MODEL
        self.tc["model"] = os.getenv("HWSKU", os.getenv("PRODUCT_MODEL"))
        self.tc["filepath"] = os.getenv("TESTFILE")
        self.tc["gtest_filter"] = os.getenv("TESTFILTER")
        logger.info("dut %s", self.tc["dut"])
        logger.info("filepath %s", self.tc["filepath"])

    def setup(self, test_context):
        """Set up SSH/SCP connections to the DUT and deploy this runner's test artifacts."""
        logger.debug("Setting up test")
        self.tc = test_context.copy()
        self.getenvvars()

        self.ssh_client = DeviceSSHClient(
            self.tc["dut"],
            device_username=self.tc["username"],
            device_password=self.tc["password"],
            debug=True,
        )
        self.scp_client = DeviceSCPClient(
            self.tc["dut"],
            device_username=self.tc["username"],
            device_password=self.tc["password"],
            debug=True,
        )
        self.connected = True

        self._deploy_artifacts()

    def _deploy_artifacts(self) -> None:
        """Deploy this runner's test binary slice onto the DUT. """
        runner_name = type(self).__name__

        # The orchestrator hands us, for this runner's STACK, either a local
        # build/fboss dir (preferred when present) or a Nexis tarball URL.
        local_dir = os.environ.get(_ENV_LOCAL_DIR[self.STACK])
        url = os.environ.get(_ENV_TARBALL_URL[self.STACK])
        if local_dir:
            namespace = f"local-{self._local_build_fingerprint(local_dir)}"
        elif url:
            # Nexis build: FBOSS_BUILD_ID is the cache/marker namespace.
            namespace = os.environ.get(_ENV_BUILD_ID)
            if not namespace:
                raise RuntimeError(
                    f"{runner_name}: {_ENV_TARBALL_URL[self.STACK]} is set but "
                    f"{_ENV_BUILD_ID} is not — the Nexis cache namespace is required."
                )
        else:
            raise RuntimeError(
                f"{runner_name} requires {_ENV_LOCAL_DIR[self.STACK]} (local build) "
                f"or {_ENV_TARBALL_URL[self.STACK]} (Nexis tarball URL).  The "
                "orchestrator (nhtests-run) sets these; pass --test-build-id or "
                "build the FBOSS stack locally."
            )

        # Bound the host cache to this single namespace — drop any other
        # build's cached contents so it can't accumulate over time.
        self._prune_stale_cache(namespace)

        # Resolve this runner's REQUIRED_PATHS to (source, archive-path) pairs.
        # Local sources are read straight from the build dir + repo; a Nexis build
        # is downloaded+extracted (and cached) first, then sliced out of that tree.
        if local_dir:
            members = self._slice_members(
                lambda rel: self._local_source_path(rel, local_dir)
            )
        else:
            extract_dir = self._ensure_extract_cached(url, namespace)
            members = self._slice_members(lambda rel: os.path.join(extract_dir, rel))

        slice_tar = self._pack_slice(runner_name, members, namespace)
        try:
            slice_sha = self._sha256(slice_tar)
            if self._is_slice_on_dut(runner_name, slice_sha):
                logger.info(
                    "%s slice already on DUT (sha %s); skipping deploy",
                    runner_name, slice_sha[:12],
                )
                return
            self._deploy_slice_to_dut(slice_tar, runner_name, slice_sha)
        finally:
            Path(slice_tar).unlink(missing_ok=True)

    @staticmethod
    def _fboss_repo_root() -> Path:
        """The fboss repo root (this file is at <root>/tests/libs/test_runner/)."""
        return Path(__file__).resolve().parents[3]

    def _local_build_fingerprint(self, build_fboss_dir: str) -> str:
        """Stable per-build id for this runner's local CMake slice. """
        h = hashlib.sha256()
        for rel in self.REQUIRED_PATHS:
            rel_clean = rel.rstrip("/")
            src = self._local_source_path(rel_clean, build_fboss_dir)
            if not os.path.isfile(src):  # not built yet, or a share/ dir
                continue
            st = os.stat(src)
            h.update(f"{rel_clean}\0{st.st_size}\0{st.st_mtime_ns}\0".encode())
        return h.hexdigest()[:16]

    @staticmethod
    def _sha256(path: str) -> str:
        """sha256 hex digest of a file, read in chunks (slices can be large)."""
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()

    def _slice_members(self, resolve) -> list[tuple[str, str]]:
        """Resolve REQUIRED_PATHS to (source_path, archive_name) pairs to pack.

        ``resolve(rel)`` maps a REQUIRED_PATHS entry (trailing "/" stripped) to its
        source on the runner host — the local build dir / repo for a local build,
        or the extracted tarball tree for a Nexis build.  The archive name is the
        relative path itself, i.e. its on-DUT location under /opt/fboss.  Packing
        straight from these sources means no staging copy is needed to line the
        archive paths up (see _pack_slice).

        Also catches drift between this runner's manifest and the build packager
        (fboss/oss/scripts/package.py): a missing source means the build
        moved/renamed something or the manifest is stale, so fail loud here rather
        than partway through running the test.
        """
        members: list[tuple[str, str]] = []
        missing: list[str] = []
        for rel in self.REQUIRED_PATHS:
            rel_clean = rel.rstrip("/")
            src = resolve(rel_clean)
            if os.path.exists(src):
                members.append((src, rel_clean))
            else:
                missing.append(rel)
        if missing:
            raise RuntimeError(
                f"{type(self).__name__} REQUIRED_PATHS not found: {missing}.  Either "
                f"fboss/oss/scripts/package.py changed what it produces, or the "
                f"runner's manifest is stale."
            )
        return members

    def _local_source_path(self, rel_dest: str, build_fboss_dir: str) -> str:
        """Map a REQUIRED_PATHS dest back to its local source.

        Mirrors fboss/oss/scripts/package.py's test_files mapping:
          - ``share/<x>``                  -> ``<repo>/fboss/oss/<x>``
          - ``bin/python_tests/<x>``       -> ``<repo>/fboss/oss/python_tests/<x>``
          - ``bin/<x>.py`` | setup_fboss_env -> ``<repo>/fboss/oss/scripts/run_scripts/<x>``
          - ``bin/<binary>``               -> ``<build_dir>/build/fboss/<binary>``
        """
        oss = self._fboss_repo_root() / "fboss" / "oss"
        if rel_dest.startswith("share/"):
            return str(oss / rel_dest[len("share/"):])
        if rel_dest.startswith("bin/python_tests/"):
            return str(oss / "python_tests" / rel_dest[len("bin/python_tests/"):])
        if rel_dest.startswith("bin/"):
            name = rel_dest[len("bin/"):]
            if name.endswith(".py") or name == "setup_fboss_env":
                return str(oss / "scripts" / "run_scripts" / name)
            return os.path.join(build_fboss_dir, name)
        raise RuntimeError(
            f"{type(self).__name__}: don't know the local source for REQUIRED_PATH "
            f"{rel_dest!r}; extend _local_source_path to match package.py."
        )

    @staticmethod
    def _prune_stale_cache(namespace: str) -> None:
        """Bound the host cache to a single namespace.

        Deletes every cache namespace other than ``namespace`` so
        can't accumulate builds over time
        """
        root = _HOST_CACHE_ROOT
        if not os.path.isdir(root):
            return
        for name in os.listdir(root):
            if name != namespace:
                logger.info("Pruning stale host cache namespace: %s", name)
                shutil.rmtree(os.path.join(root, name), ignore_errors=True)

    def _is_slice_on_dut(self, runner_name: str, slice_sha: str) -> bool:
        """True if the DUT already holds this runner's slice with the same content."""
        marker = f"{_DUT_MARKER_DIR}/{runner_name}.sha"
        exit_status, output = self.ssh_client.run_cmd(f"cat {marker} 2>/dev/null")
        return exit_status == 0 and output.strip() == slice_sha

    def _ensure_extract_cached(self, url: str, build_id: str) -> str:
        """Ensure the tarball is extracted in the host cache; return the path.

        Cache layout: the extracted contents live under
        `<cache_root>/<build_id>/<tarball-basename>/extracted/`.  Download +
        extract into a staging dir, then rename it into place.  Any leftover
        staging from a failed run is cleared on the next attempt.
        """
        tarball_name = os.path.basename(url.split("?")[0])
        cache_dir = f"{_HOST_CACHE_ROOT}/{build_id}/{tarball_name}"
        extracted_dir = f"{cache_dir}/extracted"

        if os.path.isdir(extracted_dir):
            logger.info(
                "Test artifact cache hit: build=%s tarball=%s",
                build_id, tarball_name,
            )
            return extracted_dir

        logger.info(
            "Test artifact cache miss; downloading: build=%s tarball=%s",
            build_id, tarball_name,
        )
        os.makedirs(cache_dir, exist_ok=True)
        staging = f"{cache_dir}/staging"
        shutil.rmtree(staging, ignore_errors=True)  # clear any partial leftover
        os.makedirs(staging)

        tarball_path = os.path.join(staging, "_tarball.tar.zst")
        self._fetch(url, tarball_path)
        subprocess.run(["tar", "-C", staging, "-xf", tarball_path], check=True)
        Path(tarball_path).unlink(missing_ok=True)
        os.rename(staging, extracted_dir)
        return extracted_dir

    def _pack_slice(
        self,
        runner_name: str,
        members: list[tuple[str, str]],
        namespace: str,
    ) -> str:
        """Pack this runner's slice into a tar to ship to the DUT.

        Adds each (source, archive_name) pair straight into the archive, reading
        the files in place from the local build dir / repo (or the extracted Nexis
        tree) — no staging copy is needed to line the on-DUT paths up.  Directories
        (share/) are added recursively, and tarfile carries each file's mode, so
        the exec bit on binaries survives.
        """
        slice_tar = f"{_HOST_CACHE_ROOT}/{namespace}/{runner_name}-slice.tar"
        os.makedirs(os.path.dirname(slice_tar), exist_ok=True)
        logger.info(
            "Packing slice tar: runner=%s members=%d", runner_name, len(members)
        )
        # "w" truncates, so a leftover from a previous failed run is harmless.
        with tarfile.open(slice_tar, "w") as tar:
            for src, arcname in members:
                tar.add(src, arcname=arcname)
        return slice_tar

    def _deploy_slice_to_dut(
        self, slice_tar: str, runner_name: str, slice_sha: str
    ) -> None:
        """SCP the slice tar, extract into /opt/fboss, then record its sha.

        Extract + sha-write are chained with `&&` so the marker can only hold a
        sha once the extract succeeded.  Cleanup of the slice tar on the DUT
        runs in `finally` regardless of outcome.
        """
        remote_slice = f"/tmp/fboss-{runner_name}-slice.tar"
        marker = f"{_DUT_MARKER_DIR}/{runner_name}.sha"
        try:
            logger.info("Copying slice tar to DUT at %s", remote_slice)
            exit_status, output = self.scp_client.put_file(slice_tar, remote_slice)
            if exit_status != 0:
                raise RuntimeError(
                    f"Failed to copy slice tar for {runner_name} to DUT: {output}"
                )

            logger.info(
                "Extracting slice tar on DUT into %s and recording sha %s",
                _FBOSS_ROOT_ON_DUT, slice_sha[:12],
            )
            exit_status, output = self.ssh_client.run_cmd(
                f"sudo mkdir -p {_DUT_MARKER_DIR} && "
                f"sudo tar -C {_FBOSS_ROOT_ON_DUT} -xf {remote_slice} && "
                f"echo {slice_sha} | sudo tee {marker} > /dev/null"
            )
            if exit_status != 0:
                raise RuntimeError(
                    f"Failed to extract slice tar for {runner_name} on DUT: {output}"
                )
        finally:
            cleanup_status, cleanup_output = self.ssh_client.run_cmd(
                f"sudo rm -f {remote_slice}"
            )
            if cleanup_status != 0:
                logger.warning(
                    "Failed to clean up slice tar on DUT: %s", cleanup_output
                )

        logger.info("Deployed %s test artifacts to DUT", runner_name)

    def _fetch(self, url: str, dest_path: str) -> None:
        """Fetch a Nexis tarball to dest_path on the runner host.

        Always a CloudStack HTTP(S) URL (the orchestrator only ever resolves
        *_TARBALL_URL to one); fetched with wget for parity with the prepare-side
        artifact fetch — same retry / redirect semantics, same CloudStack-friendly
        defaults.  Local builds never reach here: they're handed a *_LOCAL_DIR and
        packed straight from disk (see _deploy_artifacts / _pack_slice).
        """
        result = subprocess.run(
            ["wget", "--quiet", "--timeout=300", "--tries=3", "-O", dest_path, url],
            stderr=subprocess.PIPE,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"wget of {url} failed (exit={result.returncode}): {result.stderr.strip()}"
            )

    def set_filters(self, src_filepath, dst_filepath):
        """Create and upload test filter file to DUT."""
        logger.debug("Setting filters")
        # tc["filter"] replaces the per-test-file default filter list with
        # a single gtest-style expression
        override_filter = self.tc.get("gtest_filter")
        filters = [override_filter] if override_filter else self.tc["filters"]
        # create filters file
        with open(src_filepath, "w", encoding="utf-8") as f:
            for test_filter in filters:
                f.write(f"{test_filter}\n")
        exit_status, output = self.scp_client.put_file(src_filepath, dst_filepath)
        if exit_status != 0:
            logger.error("Failed to copy filter file: %s", output)
            return False
        return True

    def normalize_test_results_file(self):
        """Normalize test results XML file."""
        logger.info("Normalizing test results file")
        if not os.path.exists("/tmp/tr.xml"):
            logger.warning("tr.xml not found, skipping normalization")
            return
        with open("/tmp/tr.xml", encoding="utf-8") as f:
            lines = f.readlines()

        with open("/tmp/tr.xml", "w", encoding="utf-8") as f:
            for line in lines:
                if line.strip().startswith("<testsuite"):
                    line = line.replace(
                        'name="AllTests"', f'name="{self.tc["filepath"]}"'
                    )
                elif line.strip().startswith("<testcase"):
                    classname = line.split('classname="')[1].split('"')[0]
                    classname = classname.split("/")[0]
                    name = line.split('name="')[1].split('"')[0]
                    line = line.replace(f'name="{name}"', f'name="{classname}.{name}"')
                f.write(line)

    def binary_exit_is_fatal(self, exit_status: int) -> bool:
        return exit_status != 0

    def _merge_junit_results(
        self,
        passes: list[tuple[str, str, str]],
        skipped: list[tuple[str, str]] = (),
    ) -> None:
        """Merge multiple (label, log_local, xml_local) pass results, plus a
        synthetic <skipped> testcase per (pattern, reason) in ``skipped``,
        into /tmp/test.log and /tmp/tr.xml.
        """
        testsuites_el = ET.Element("testsuites")
        merged = ET.SubElement(testsuites_el, "testsuite", {
            "tests": "0", "failures": "0", "errors": "0",
            "disabled": "0", "skipped": "0", "time": "0",
            "timestamp": "", "name": "AllTests",
        })
        totals = {"tests": 0, "failures": 0, "errors": 0, "disabled": 0, "skipped": 0}
        total_time = 0.0
        log_parts = []

        for label, log_local, xml_local in passes:
            if os.path.exists(log_local):
                with open(log_local, encoding="utf-8", errors="replace") as f:
                    log_parts.append(f"\n===== {label} pass =====\n{f.read()}")
            if os.path.exists(xml_local):
                try:
                    suite = ET.parse(xml_local).getroot().find("testsuite")
                except ET.ParseError as e:
                    logger.warning(
                        "Failed to parse %s pass results %s: %s", label, xml_local, e
                    )
                    suite = None
                if suite is not None:
                    for tc in suite.findall("testcase"):
                        merged.append(tc)
                    for key in totals:
                        totals[key] += int(suite.get(key, 0) or 0)
                    total_time += float(suite.get("time", 0) or 0)
                    if not merged.get("timestamp"):
                        merged.set("timestamp", suite.get("timestamp", ""))

        for pattern, reason in skipped:
            tc = ET.SubElement(merged, "testcase", {
                "name": pattern.strip("*"), "classname": "Skipped", "time": "0",
            })
            ET.SubElement(tc, "skipped", {"message": reason})
            totals["tests"] += 1
            totals["skipped"] += 1
            log_parts.append(f"\n===== pass skipped ({reason}): {pattern} =====\n")

        for key, value in totals.items():
            merged.set(key, str(value))
        merged.set("time", f"{total_time:.3f}")

        ET.indent(testsuites_el)
        ET.ElementTree(testsuites_el).write("/tmp/tr.xml", encoding="UTF-8", xml_declaration=True)
        with open("/tmp/test.log", "w", encoding="utf-8") as f:
            f.write("\n".join(log_parts))

    def _execute_test_binary(
        self, model: str, log_local: str, xml_local: str, skip_tr_xml: bool
    ) -> bool:
        """Clear local+remote result files, run the test binary once, fetch results.

        Returns True if the fetch succeeded and the binary's exit status
        isn't fatal.
        """
        for local_path in (log_local, xml_local):
            if os.path.exists(local_path):
                os.unlink(local_path)

        if not self.set_filters("/tmp/tests.conf", self.filter_filepath):
            return False

        cmd = f"sudo rm -f {self.testlog_filepath} {self.testresult_filepath}"
        exit_status, output = self.ssh_client.run_cmd(cmd)
        if exit_status != 0:
            logger.error("Failed to run command: %s %s", cmd, output)
            return False

        cmd = self.build_test_cmd(model)
        logger.info("Running remote command: %s", cmd)
        test_exit_status, test_output = self.ssh_client.run_cmd(cmd)

        exit_status, output = self.scp_client.get_file(self.testlog_filepath, log_local)
        if exit_status != 0:
            logger.error("Failed to fetch test logs: %s", output)
            return False

        if not skip_tr_xml:
            exit_status, output = self.scp_client.get_file(
                self.testresult_filepath, xml_local
            )
            if exit_status != 0:
                logger.warning(
                    "Failed to fetch test results (tr.xml may not exist if binary crashed): %s",
                    output,
                )

        if self.binary_exit_is_fatal(test_exit_status):
            logger.error("Failed to run tests: %s", test_output)
            return False
        return True

    def pre_test(self):
        """Wipe stale agent-ensemble state before each test.

        AgentEnsemble::setBootType picks WARM_BOOT iff
        <warm_boot_dir>/can_warm_boot exists, but only the COLD_BOOT path
        in AgentEnsemble::setupEnsemble writes agent.conf. A stale marker
        without a paired agent.conf wedges every test in SetUp() with
        'unable to read .../agent.conf'. This is the dominant TE failure
        mode (~43% of FAIL runs in T-Recs over the last month) because
        TE batches run back-to-back without re-imaging between them,
        unlike devs who install fresh images per run.

        Force a known cold-boot state on every invocation by removing the
        can_warm_boot marker (so setBootType returns COLD_BOOT) and the
        agent_ensemble dir (so the cold-boot path writes a fresh
        agent.conf from --config). AgentEnsemble re-creates the dir via
        utilCreateDir(), so removal is safe.
        """
        cmd = (
            f"sudo rm -f {_WARM_BOOT_DIR}/can_warm_boot* "
            f"&& sudo rm -rf {_AGENT_ENSEMBLE_DIR}"
        )
        exit_status, output = self.ssh_client.run_cmd(cmd)
        if exit_status != 0:
            logger.warning("pre_test state cleanup failed: %s", output)

    def post_test(self):
        pass

    def build_test_cmd(self, model: str) -> str:
        test_args = self.test_args(model)
        logging_arg = f" --fboss_logging {self._fboss_logging}" if self._fboss_logging else ""
        return (
            f"sudo su -c 'cd /opt/fboss && source ./bin/setup_fboss_env && "
            f" ./bin/run_test.py {test_args} --filter_file={self.filter_filepath}{logging_arg} "
            f"' > {self.testlog_filepath} 2>&1"
        )

    @_enforce_min_failure_duration
    def run_test(self, test_context, skip_tr_xml=False, fboss_logging=None):
        """Connect to the DUT, deploy this runner's artifacts, then run the test.

        Template method — do NOT override in subclasses. setup() (SSH/SCP
        connect + _deploy_artifacts) and the deploy-only gate live here so every
        runner deploys identically and honors --mode deploy; a subclass that
        reimplemented run_test() could silently skip the gate. Subclasses
        customize execution by overriding _run_test_impl() instead.

        fboss_logging overrides the test binary's --fboss_logging level for this
        run (default: run_test.py's own DBG4).
        """
        self._fboss_logging = fboss_logging
        logger.info("Running tests")
        self.setup(test_context)

        # Deploy-only: setup() has uploaded this runner's artifact slice to the
        # DUT.  Stop here without running the test binary — nhtests-run
        # --mode deploy sets this to stage artifacts without executing tests.
        if os.environ.get(_ENV_DEPLOY_ONLY) == _ENV_DEPLOY_ONLY_ON:
            logger.info(
                "%s: %s set; artifacts deployed, skipping test execution",
                type(self).__name__, _ENV_DEPLOY_ONLY,
            )
            return True

        return self._run_test_impl(test_context, skip_tr_xml=skip_tr_xml)

    def _run_test_impl(self, test_context, skip_tr_xml=False):
        """Run the hardware test on the DUT.

        Called by run_test() after setup()/deploy, so it starts from a
        connected, artifact-staged DUT. Override per runner to customize
        execution (see SmokeTestRunner, BenchmarkTestRunner).
        """
        for local_path in ("/tmp/test.log", "/tmp/tr.xml"):
            if os.path.exists(local_path):
                os.unlink(local_path)

        status = self.set_filters("/tmp/tests.conf", self.filter_filepath)
        if not status:
            return False

        model = _normalize_model(self.tc["model"])

        self.pre_test()
        try:
            success = self._execute_test_binary(
                model, "/tmp/test.log", "/tmp/tr.xml", skip_tr_xml
            )
        finally:
            self.post_test()

        if not skip_tr_xml:
            self.normalize_test_results_file()

        return success

    def close(self):
        """Close connections."""
        self.connected = False


# Concrete test runner implementations


class SaiTestRunner(BaseHwTestRunner):
    """Runner for SAI hardware tests."""

    def test_args(self, model: str) -> str:
        config_name = _SAI_AGENT_CONFIG_NAME.get(model, model)
        logger.info("model=%s hw_test_config=%s", model, config_name)
        return f"sai --config ./share/hw_test_configs/{config_name}.agent.materialized_JSON{_sai_skip_known_bad(model)}"
    STACK = _STACK_FORWARDING
    BINARIES = ("bin/sai_test-sai_impl",)
    REQUIRED_PATHS = (*BINARIES, *_STACK_SHARE[STACK])


class LedTestRunner(BaseHwTestRunner):
    """Runner for LED service hardware tests.

    led_service_hw_test ships in the forwarding tarball. It reads its platform
    from /etc/coop/led.conf on the DUT, so no --config is passed — run_test.py
    led just runs the binary against the wrapper's filter file. Only the binary
    is sliced; the runner needs none of the forwarding share/ configs.
    """

    def test_args(self, model: str) -> str:  # noqa: ARG002
        return "led"
    STACK = _STACK_FORWARDING
    BINARIES = ("bin/led_service_hw_test",)
    REQUIRED_PATHS = BINARIES


class SaiAgentTestRunner(BaseHwTestRunner):
    """Runner for SAI agent tests."""

    STACK = _STACK_FORWARDING
    # Both binaries ship: --agent-run-mode picks mono vs multi at run time.
    BINARIES = ("bin/sai_agent_hw_test-sai_impl", "bin/multi_switch_agent_hw_test")
    REQUIRED_PATHS = (*BINARIES, *_STACK_SHARE[STACK])

    @staticmethod
    def _enable_production_features(model: str) -> str:
        PROD_FEEATURES_KEY: dict[str, str] = {
            "minipack3": "tomahawk5",
            "wedge800bact": "tomahawk5",
            "wedge800bnhp": "tomahawk5",
            "nhbw800f": "tomahawk5",
            "wedge800cact": "g202x",
            "nhcw800f": "g202x",
            "nh4010f": "tomahawk5",
            "nh4215f": "tomahawk6",
            "nh4220f": "tomahawk6",
        }
        key = PROD_FEEATURES_KEY.get(model)
        return f" --enable-production-features {key}" if key else ""

    def test_args(self, model: str) -> str:
        config_name = _SAI_AGENT_CONFIG_NAME.get(model, model)
        logger.info("model=%s hw_test_config=%s", model, config_name)
        return f"sai_agent --config ./share/hw_test_configs/{config_name}.agent.materialized_JSON \
            {_sai_skip_known_bad(model)}{self._enable_production_features(model)}"


class _CablingAwareRunnerMixin:
    """Copper-safe vs optics-only filter split, shared by QsfpTestRunner and
    LinkTestRunner. Subclasses set _OPTICS_ONLY_FILTER_SUBSTRINGS and may
    override _prepare_pass() if the DUT config needs to change per pass.
    """

    _OPTICS_ONLY_FILTER_SUBSTRINGS: tuple[str, ...] = ()
    _PORTS_INFO_ENV_VAR = "TEST_PORTS_INFO"
    _SNAKE_PAIRS_ENV_VAR = "TEST_SNAKE_PAIRS"

    def __init__(self):
        super().__init__()
        self._cached_base_config = None
        self._cached_port_map = None

    def _load_snake_pairs(self) -> dict[str, str]:
        return _load_json_pairs(os.getenv(self._SNAKE_PAIRS_ENV_VAR))

    def _load_base_config_and_port_map(self, base_config_dir: Path, config_name: str) -> tuple[dict, dict]:
        """Load and cache the base config JSON + platform-mapping port map.

        _prepare_pass() is called once per pass (main/optics), and both inputs
        are the same across passes for a given run, so cache them on first
        load instead of re-reading + re-parsing per pass.
        """
        if self._cached_base_config is None:
            base_path = _repo_dir(base_config_dir) / f"{config_name}.materialized_JSON"
            try:
                with open(base_path, encoding="utf-8") as f:
                    self._cached_base_config = json.load(f)
            except (OSError, ValueError) as e:
                raise RuntimeError(f"Failed to load base config {base_path}: {e}") from e
            self._cached_port_map = _load_platform_mapping(config_name)
        return self._cached_base_config, self._cached_port_map

    def _prepare_pass(self, model: str, ports: list[str]) -> None:  # noqa: ARG002
        pass

    def _load_cabling(self, cabling_path: str) -> tuple[list[str], list[str], dict[str, str | None]]:
        """Parse TEST_PORTS_INFO: {port: {"is_copper": bool | None, "media_interface": str | None}}.

        Returns (all_ports, optics_ports, media_by_port); unknown media type
        counts toward all_ports but not optics_ports.
        """
        try:
            with open(cabling_path, encoding="utf-8") as f:
                cabling = json.load(f)
        except (OSError, ValueError) as e:
            raise RuntimeError(f"Failed to load ports-info file {cabling_path}: {e}") from e
        all_ports = list(cabling)
        optics_ports = [p for p, info in cabling.items() if info.get("is_copper") is False]
        media_by_port = {p: info.get("media_interface") for p, info in cabling.items()}
        return all_ports, optics_ports, media_by_port

    def _gate_filters(
        self, patterns: list[str], media_by_port: dict[str, str | None], optics_ports: list[str]
    ) -> tuple[list[str], list[tuple[str, str]]]:
        """Hook for cabling-aware filter gating. Base impl is a no-op (keeps
        all patterns); LinkTestRunner overrides to drop patterns the DUT's
        cabling can't satisfy."""
        return list(patterns), []

    @classmethod
    def _split_filters(cls, filters: list[str]) -> tuple[list[str], list[str]]:
        """Bucket filters by substring match against optics-only test names."""
        copper_safe, optics_only = [], []
        for f in filters:
            bucket = optics_only if any(s in f for s in cls._OPTICS_ONLY_FILTER_SUBSTRINGS) else copper_safe
            bucket.append(f)
        return copper_safe, optics_only

    @staticmethod
    def _parse_gtest_filter(expr: str) -> tuple[list[str], str]:
        """Split a --gtest_filter expression into its positive patterns and shared
        negative-pattern suffix.

        gtest's own filter grammar is positives['-'negatives], split on the first '-'.
        """
        positive, sep, negative = expr.partition("-")
        patterns = [p for p in positive.split(":") if p]
        if not patterns and sep:
            # "-foo" alone means "everything except foo" (gtest defaults the
            # positive side to "*"); an empty positive here is not "no tests".
            patterns = ["*"]
        suffix = f"-{negative}" if sep else ""
        return patterns, suffix

    @classmethod
    def _bucket_expressions(cls, patterns: list[str], suffix: str) -> tuple[str, str]:
        """Bucket patterns, then rejoin each side into a --gtest_filter expression."""
        copper_safe, optics_only = cls._split_filters(patterns)
        copper_expr = ":".join(copper_safe) + suffix if copper_safe else ""
        optics_expr = ":".join(optics_only) + suffix if optics_only else ""
        return copper_expr, optics_expr

    @classmethod
    def _split_gtest_filter(cls, expr: str) -> tuple[str, str]:
        """Split a single --gtest_filter expression into copper-safe/optics-only
        sub-expressions, sharing the negative-pattern suffix.

        Colon-separated positives are classified the same way _split_filters
        buckets tc["filters"], so a mixed TESTFILTER runs as two passes against
        the right port set each, instead of once against the wrong one.
        """
        return cls._bucket_expressions(*cls._parse_gtest_filter(expr))

    def _pass_local_paths(self, label: str) -> tuple[str, str]:
        prefix = type(self).__name__.lower()
        return (f"/tmp/{prefix}_test_{label}.log", f"/tmp/{prefix}_tr_{label}.xml")

    def _run_test_impl(self, test_context, skip_tr_xml=False):
        # Override _run_test_impl (not run_test) so the base run_test template
        # runs setup()/deploy and the deploy-only gate for every path,
        # including the cabling-aware one, and pads a failing run at most once.
        cabling_path = os.getenv(self._PORTS_INFO_ENV_VAR)
        if not cabling_path:
            return super()._run_test_impl(test_context, skip_tr_xml)
        return self._run_cabling_aware(cabling_path, test_context, skip_tr_xml)

    def _run_cabling_aware(self, cabling_path, test_context, skip_tr_xml):
        # setup()/deploy already ran in the base run_test() before this call.
        model = _normalize_model(self.tc["model"])
        all_ports, optics_ports, media_by_port = self._load_cabling(cabling_path)

        gtest_filter = self.tc.get("gtest_filter")
        if gtest_filter:
            patterns, suffix = self._parse_gtest_filter(gtest_filter)
        else:
            patterns, suffix = list(self.tc["filters"]), ""

        kept_patterns, skipped = self._gate_filters(patterns, media_by_port, optics_ports)
        if gtest_filter:
            copper_bucket, optics_bucket = self._bucket_expressions(kept_patterns, suffix)
        else:
            copper_bucket, optics_bucket = self._split_filters(kept_patterns)

        passes = []  # list of (label, filter_value, ports)
        if copper_bucket:
            passes.append(("main", copper_bucket, all_ports))
        if optics_bucket:
            if optics_ports:
                passes.append(("optics", optics_bucket, optics_ports))
            else:
                logger.info(
                    "No optics/active-cabled ports on this DUT; skipping optics-only tests: %s",
                    optics_bucket,
                )
                skipped.extend(
                    (pattern, "no optical/active transceivers cabled on this DUT")
                    for pattern in ([optics_bucket] if gtest_filter else optics_bucket)
                )

        if not passes and not skipped:
            logger.warning("%s: no filters to run", type(self).__name__)
            return True

        original_filters = self.tc["filters"]
        original_gtest_filter = gtest_filter
        pass_results = []
        ran_labels = []
        pre_test_called = False
        try:
            for label, filter_value, ports in passes:
                if gtest_filter:
                    self.tc["gtest_filter"] = filter_value
                else:
                    self.tc["filters"] = filter_value
                self._prepare_pass(model, ports)
                self.pre_test()  # fresh warm/cold-boot state wipe per pass
                pre_test_called = True
                log_local, xml_local = self._pass_local_paths(label)
                success = self._execute_test_binary(model, log_local, xml_local, skip_tr_xml)
                pass_results.append(success)
                ran_labels.append(label)
                if not success:
                    logger.error("%s %s pass failed; aborting remaining passes", type(self).__name__, label)
                    for _, remaining, _ in passes[len(ran_labels):]:
                        skipped.extend(
                            (pattern, "earlier pass failed; run aborted")
                            for pattern in ([remaining] if gtest_filter else remaining)
                        )
                    break
        finally:
            self.tc["filters"] = original_filters
            if gtest_filter:
                self.tc["gtest_filter"] = original_gtest_filter
            if pre_test_called:
                self.post_test()

        if not skip_tr_xml:
            self._merge_junit_results(
                [(label, *self._pass_local_paths(label)) for label in ran_labels],
                skipped=skipped,
            )
            self.normalize_test_results_file()

        return all(pass_results)


class QsfpTestRunner(_CablingAwareRunnerMixin, BaseHwTestRunner):
    """Runner for QSFP hardware tests."""

    STACK = _STACK_FORWARDING
    BINARIES = ("bin/qsfp_hw_test",)
    REQUIRED_PATHS = (*BINARIES, *_STACK_SHARE[STACK])

    _BASE_CONFIG_DIR = Path("fboss/oss/qsfp_test_configs")
    _REMOTE_CONFIG_PATH = "/home/netops/qsfp_test.materialized_JSON"
    _FALLBACK_PROFILE_ID = 38

    # These hard-assert a non-empty optical/active transceiver set.
    _OPTICS_ONLY_FILTER_SUBSTRINGS = (
        "i2cStressWrite",
        "i2cLogCapacityWrite",
        "cmisPageChange",
        "verifyResetControl",
    )

    def _pair_profile_id(self, a_port: str, z_port: str, port_map: dict) -> int:
        # Both ends of a pair get the same profile (HwPortUtils::getCabledPortsAndProfiles),
        # so pick the narrower end rather than risk asking for more than one side supports.
        a_info, z_info = port_map.get(a_port), port_map.get(z_port)
        if not a_info or not z_info:
            return self._FALLBACK_PROFILE_ID
        return min(a_info, z_info, key=lambda info: info.speed).profile_id

    def _build_cabled_config(self, base_config: dict, ports: list[str], port_map: dict, pairs: dict) -> dict:
        config = copy.deepcopy(base_config)
        cabled = []
        for port in ports:
            info = port_map.get(port)
            profile_id = info.profile_id if info else self._FALLBACK_PROFILE_ID
            cabled.append({"aPortName": port, "zPortName": port, "profileID": profile_id})
        # Appended after every self-pair, on purpose: the hw test's neighbor map is
        # keyed by transceiver id and last-write-wins, so a real pair must come after
        # that transceiver's self-pair to actually take effect.
        neighbors = _neighbor_pairs(ports, pairs)
        for a, z in neighbors:
            cabled.append({"aPortName": a, "zPortName": z, "profileID": self._pair_profile_id(a, z, port_map)})
        config["qsfpTestConfig"]["cabledPortPairs"] = cabled
        logger.info("qsfp cabled pairs: %d neighbor pairs added for %d ports", len(neighbors), len(ports))
        # Skip discovery-time firmware upgrade: fails when fboss_firmware.yaml is missing.
        args = config.setdefault("defaultCommandLineArgs", {})
        args["firmware_upgrade_on_coldboot"] = "false"
        args["firmware_upgrade_on_tcvr_insert"] = "false"
        return config

    def _prepare_pass(self, model: str, ports: list[str]) -> None:
        config_name = _LINK_QSFP_TEST_CONFIG_NAME.get(model, model)
        base_config, port_map = self._load_base_config_and_port_map(self._BASE_CONFIG_DIR, config_name)
        config = self._build_cabled_config(base_config, ports, port_map, self._load_snake_pairs())
        self._upload_generated_config(config)

    def test_args(self, model: str) -> str:
        if self._use_generated_config:
            return f"qsfp --qsfp-config {self._REMOTE_CONFIG_PATH}"
        config_name = _LINK_QSFP_TEST_CONFIG_NAME.get(model, model)
        return f"qsfp --qsfp-config ./share/qsfp_test_configs/{config_name}.materialized_JSON"


class LinkTestRunner(_CablingAwareRunnerMixin, BaseHwTestRunner):
    """Runner for link tests."""

    # Must stay in step with the PRBS_*_TEST instantiations in AgentEnsemblePrbsTest.cpp.
    _MEDIA_INTERFACE_TOKENS = (
        "FR1_100G",
        "FR4_200G",
        "FR4_400G",
        "DR4_400G",
        "CR4_400G",
        "CR8_800G",
        "FR8_800G",
        "DR4_800G",
    )

    # These hard-assert a non-empty optical/active transceiver set. CR codes belong
    # here too: the PRBS pair source drops passive copper before checkValidMedia runs.
    _OPTICS_ONLY_FILTER_SUBSTRINGS = (
        "verifyTxRxLatches",
        "opticsTxDisableRandomPorts",
        "opticsTxDisableEnable",
        "opticsVdmPerformanceMonitoring",
        *_MEDIA_INTERFACE_TOKENS,
    )

    # TCVR_L-to-TCVR_L programs PRBS on both ends of a pair; ASIC-to-TCVR_S only on
    # the one port it tests. Matched against the generated class names.
    _BOTH_ENDS_TOKEN = "TCVR_L"

    _BASE_CONFIG_DIR = Path("fboss/oss/link_test_configs")
    _REMOTE_CONFIG_PATH = "/home/netops/link_test_config.materialized_JSON"
    _SYSTEM_QSFP_CONFIG_PATH = "/etc/coop/qsfp.conf"
    _REMOTE_QSFP_CONFIG_PATH = "/home/netops/link_test_qsfp.conf"
    # JSON map key for LLDPTag.PORT: see fboss/agent/switch_config.thrift.
    _LLDP_PORT_TAG = "2"

    STACK = _STACK_FORWARDING
    # Both binaries ship: --agent-run-mode picks mono vs multi at run time.
    BINARIES = ("bin/sai_mono_link_test-sai_impl", "bin/sai_multi_link_test-sai_impl")
    REQUIRED_PATHS = (*BINARIES, *_STACK_SHARE[STACK])

    def __init__(self):
        super().__init__()
        self._use_generated_qsfp = False
        self._pass_ports: list[str] | None = None

    def _prepare_pass(self, model: str, ports: list[str]) -> None:  # noqa: ARG002
        self._pass_ports = ports

    @classmethod
    def _media_token_in(cls, pattern: str) -> str | None:
        return next((token for token in cls._MEDIA_INTERFACE_TOKENS if token in pattern), None)

    @classmethod
    def _media_cabled(
        cls, pattern: str, media: str, media_by_port: dict[str, str | None], pairs: dict[str, str]
    ) -> bool:
        if not pairs:
            # No pairs to check ends against; fall back to "cabled anywhere".
            return media in media_by_port.values()
        if cls._BOTH_ENDS_TOKEN in pattern:
            return any(
                media_by_port.get(port) == media and media_by_port.get(peer) == media
                for port, peer in pairs.items()
            )
        return any(media_by_port.get(port) == media for port in pairs)

    def _gate_filters(
        self, patterns: list[str], media_by_port: dict[str, str | None], optics_ports: list[str]
    ) -> tuple[list[str], list[tuple[str, str]]]:
        """Keep only patterns whose referenced media is actually cabled on this DUT.

        PRBS patterns naming no media are gated too: they would expand to every
        media-templated class, including ones with no ports, and abort the binary.
        """
        optical = set(optics_ports)
        eligible = {p: m for p, m in media_by_port.items() if p in optical}
        pairs = {p: peer for p, peer in self._load_snake_pairs().items() if p in eligible and peer in eligible}
        kept, skipped = [], []
        for pattern in patterns:
            media = self._media_token_in(pattern)
            if media is None and "Prbs" not in pattern:
                kept.append(pattern)
            elif media is None:
                # Must precede the no-optics case: such a pattern is copper-safe, so
                # it would otherwise reach the main pass and abort the binary there.
                skipped.append((pattern, "PRBS filter names no media interface"))
            elif not eligible:
                # No optical/active ports at all; the optics-pass check reports that.
                kept.append(pattern)
            elif not any(eligible.values()):
                skipped.append((pattern, "port media interface unavailable"))
            elif self._media_cabled(pattern, media, eligible, pairs):
                kept.append(pattern)
            else:
                skipped.append((pattern, f"no {media} optics cabled on this DUT"))
        return kept, skipped

    @classmethod
    def _config_name(cls, model: str) -> str:
        return _LINK_QSFP_TEST_CONFIG_NAME.get(model, model)

    @classmethod
    def _synthesize_port(
        cls,
        base_json: dict,
        port_map: dict[str, _PortInfo],
        name: str,
        vlan_id: int,
        template: _PortTemplate,
    ) -> dict:
        info = port_map.get(name)
        if info is None:
            raise ValueError(f"netbox port {name} is not in the platform mapping")
        sw = base_json["sw"]
        # The agent requires every port to own exactly one interface, so a synthesized
        # port needs a matching vlan, vlanPort and interface too.
        port = copy.deepcopy(template.port)
        port.update(
            {
                "logicalID": info.logical_id,
                "name": name,
                "state": 2,
                "speed": info.speed,
                "profileID": info.profile_id,
                "ingressVlan": vlan_id,
                "portType": 0,
                "expectedLLDPValues": {},
            }
        )
        vlan = copy.deepcopy(template.vlan)
        vlan.update({"id": vlan_id, "intfID": vlan_id, "name": f"vlan{vlan_id}"})
        vlan_port = copy.deepcopy(template.vlan_port)
        vlan_port.update({"vlanID": vlan_id, "logicalPort": info.logical_id})
        intf = copy.deepcopy(template.interface)
        # Synthesized, not inherited from the base config: the fboss ECMP helper
        # skips IP-less interfaces, silently dropping the port from L3 tests.
        intf.update(
            {
                "intfID": vlan_id,
                "vlanID": vlan_id,
                "ipAddresses": [
                    f"2600:0:0:{vlan_id:x}::/64",
                    f"100.{64 + (vlan_id >> 8)}.{vlan_id & 0xFF}.0/24",
                ],
            }
        )
        sw["ports"].append(port)
        sw["vlans"].append(vlan)
        sw["vlanPorts"].append(vlan_port)
        sw["interfaces"].append(intf)
        return port

    @classmethod
    def _overlay_cabling(
        cls,
        base_json: dict,
        pairs: dict[str, str],
        port_map: dict[str, _PortInfo],
    ) -> dict:
        if not pairs:
            raise ValueError("refusing to generate link test config: no cabling pairs")
        sw = base_json["sw"]
        template_vlan_id = sw["ports"][0]["ingressVlan"]
        template = _PortTemplate(
            port=sw["ports"][0],
            vlan=next(v for v in sw["vlans"] if v["id"] == template_vlan_id),
            vlan_port=next(p for p in sw["vlanPorts"] if p["vlanID"] == template_vlan_id),
            interface=next(i for i in sw["interfaces"] if i.get("vlanID") == template_vlan_id),
        )
        # Re-synthesize all front-panel ports from the platform mapping and
        # netbox cabling; the base config contributes only non-port scaffolding
        # and non-front-panel ports (mgmt, fabric/recycle).
        sw["ports"] = [p for p in sw["ports"] if p["portType"] != 0]
        kept_vlans = {p["ingressVlan"] for p in sw["ports"]} | {sw.get("defaultVlan")}
        sw["vlans"] = [v for v in sw["vlans"] if v["id"] in kept_vlans]
        sw["vlanPorts"] = [vp for vp in sw["vlanPorts"] if vp["vlanID"] in kept_vlans]
        sw["interfaces"] = [
            i for i in sw["interfaces"] if "vlanID" not in i or i["vlanID"] in kept_vlans
        ]
        for port in sw["ports"]:
            port["expectedLLDPValues"] = {}
        used_vlans = {v["id"] for v in sw["vlans"]}
        # Allocate from the "type-1" interface band (2000-2251).
        free_vlans = (v for v in range(2000, 2252) if v not in used_vlans)
        try:
            for name, peer in pairs.items():
                port = cls._synthesize_port(base_json, port_map, name, next(free_vlans), template)
                port["expectedLLDPValues"] = {cls._LLDP_PORT_TAG: peer}
            # The SDK exposes SAI port objects for every cage's default port
            # regardless of config, and warmboot aborts on port objects the
            # config doesn't claim. Cover every cage without a cabled pair
            # with its controlling port, disabled so it never links up.
            cabled_cages = {name.rsplit("/", 1)[0] for name in pairs}
            kept_names = {p["name"] for p in sw["ports"]}
            for name in sorted(port_map):
                if (
                    not name.startswith("eth")
                    or not name.endswith("/1")
                    or name.rsplit("/", 1)[0] in cabled_cages
                    or name in kept_names
                ):
                    continue
                port = cls._synthesize_port(base_json, port_map, name, next(free_vlans), template)
                port["state"] = 1
        except StopIteration:
            raise ValueError(
                "ran out of vlans in the 2000-2251 band while synthesizing ports"
            ) from None
        return base_json

    def _stage_qsfp_config(self):
        # The agent doesn't publish port status to FSDB in time, so a qsfp_service
        # that subscribes to FSDB never sees a transceiver reach ACTIVE. Disable
        # the subscription so qsfp polls getPortStatus() directly.
        with tempfile.NamedTemporaryFile(suffix=".conf", delete=False) as f:
            local_path = f.name
        try:
            exit_status, output = self.scp_client.get_file(
                self._SYSTEM_QSFP_CONFIG_PATH, local_path
            )
            if exit_status != 0:
                raise RuntimeError(f"Failed to fetch system qsfp config: {output}")
            with open(local_path, encoding="utf-8") as f:
                qsfp = json.load(f)
            qsfp.setdefault("defaultCommandLineArgs", {})[
                "subscribe_to_state_from_fsdb"
            ] = "false"
            with open(local_path, "w", encoding="utf-8") as f:
                json.dump(qsfp, f, indent=4)
            exit_status, output = self.scp_client.put_file(
                local_path, self._REMOTE_QSFP_CONFIG_PATH
            )
        finally:
            os.unlink(local_path)
        if exit_status != 0:
            raise RuntimeError(f"Failed to upload generated qsfp config: {output}")
        self._use_generated_qsfp = True

    def pre_test(self):
        super().pre_test()

        model = _normalize_model(self.tc["model"])
        self._stage_qsfp_config()

        # Set by the nhtest executor to a {port: peer_port} JSON file (TEST_SNAKE_PAIRS)
        # when cabling was generated from netbox; absent for standalone dev runs.
        pairs = self._load_snake_pairs()
        if not pairs:
            return

        if self._pass_ports is not None:
            allowed = set(self._pass_ports)
            pairs = {port: peer for port, peer in pairs.items() if port in allowed and peer in allowed}
        # The pairs come from netbox while _pass_ports comes from the DUT, so a
        # documented cable whose optic is absent drops out here. Falling back to the
        # stock config beats letting _overlay_cabling raise mid-run, which would skip
        # post_test and leave fsdb/qsfp_service stopped.
        if not pairs:
            logger.warning("No cabled pairs left after filtering to this pass's ports; using the stock config")
            # An earlier pass may have uploaded one; don't silently reuse its cabling.
            self._use_generated_config = False
            return

        config_name = self._config_name(model)
        base_config, port_map = self._load_base_config_and_port_map(self._BASE_CONFIG_DIR, config_name)
        config = self._overlay_cabling(copy.deepcopy(base_config), pairs, port_map)
        self._upload_generated_config(config)

    def test_args(self, model: str) -> str:
        if self._use_generated_config:
            config_arg = self._REMOTE_CONFIG_PATH
        else:
            config_arg = f"./share/link_test_configs/{self._config_name(model)}.materialized_JSON"
        qsfp_arg = (
            self._REMOTE_QSFP_CONFIG_PATH
            if self._use_generated_qsfp
            else self._SYSTEM_QSFP_CONFIG_PATH
        )
        return (
            f"link --config {config_arg} --qsfp-config {qsfp_arg}"
        )

    def post_test(self):
        # The link gtest stops production qsfp_service / fsdb (via the
        # internal cleanup_*_service helpers) but never restarts them.
        self.ssh_client.run_cmd("sudo systemctl start fsdb qsfp_service")


class PlatformTestRunner(BaseHwTestRunner):
    """Runner for platform services hardware tests.

    Supports all platform test types via the --type flag:
    platform_hw_test, fan_service_hw_test, sensor_service_hw_test,
    fw_util_hw_test, weutil_hw_test, data_corral_service_hw_test,
    platform_manager_hw_test.
    """

    STACK = _STACK_PLATFORM
    BINARIES = (
        "bin/platform_hw_test",
        "bin/fan_service_hw_test",
        "bin/sensor_service_hw_test",
        "bin/fw_util_hw_test",
        "bin/weutil_hw_test",
        "bin/data_corral_service_hw_test",
        "bin/platform_manager_hw_test",
    )
    # run_test.py and setup_fboss_env come from the production image already on
    # the DUT (same as the forwarding runners and BspTestRunner), so only the
    # test binaries ship. Platform tests read no share/ configs
    # (_STACK_SHARE[platform] is empty).
    REQUIRED_PATHS = (*BINARIES, *_STACK_SHARE[STACK])

    def __init__(self, test_type="platform_hw_test"):
        super().__init__()
        self.test_type = test_type

    def test_args(self, model: str) -> str:
        return f"platform --type {self.test_type}"


class BspTestRunner(BaseHwTestRunner):
    """Runner for BSP hardware tests. Delegates to run_test.py bsp.

    All service lifecycle management (fan_service, qsfp_service, led_service
    stop/start, platform_manager restart, /run/devmap wait) and the
    --enable_stress_tests flag are handled on-DUT by run_test.py bsp.
    """
    STACK = _STACK_PLATFORM
    BINARIES = ("bin/bsp_tests",)
    REQUIRED_PATHS = (*BINARIES, *_STACK_SHARE[STACK])

    def test_args(self, model: str) -> str:
        return "bsp"

    def set_filters(self, src_filepath, dst_filepath):
        """BSP runs all cases via run_test.py bsp — no filter file needed."""
        return True

    def build_test_cmd(self, model: str) -> str:
        # Omit --filter_file so run_test.py bsp runs all cases (see set_filters).
        return (
            f"sudo su -c 'cd /opt/fboss && source ./bin/setup_fboss_env && "
            f" ./bin/run_test.py {self.test_args(model)} "
            f"' > {self.testlog_filepath} 2>&1"
        )


class SmokeTestRunner(BaseHwTestRunner):
    """Runner for the FBOSS agent smoke test.

    Unlike the gtest-based runners above, this one invokes
    ``agent_smoke.py`` directly on the DUT — no filter file, no
    ``run_test.py`` indirection — and consumes the JUnit XML it produces
    at ``self.testresult_filepath``.
    """

    # agent_smoke.py and junit.py live in the forwarding test tarball under
    # bin/python_tests/ — see FORWARDING_TEST_EXTRA in
    # fboss/oss/scripts/package.py.
    STACK = _STACK_FORWARDING
    # Smoke drives agent_smoke.py directly (no run_test.py, no share configs),
    # so it ships only its scripts — not the forwarding share tree.
    BINARIES = (
        "bin/python_tests/agent_smoke.py",
        "bin/python_tests/junit.py",
    )
    REQUIRED_PATHS = BINARIES

    AGENT_SMOKE_PATH = "/opt/fboss/bin/python_tests/agent_smoke.py"

    def test_args(self, model: str) -> str:
        # Unused; SmokeTestRunner overrides _run_test_impl (drives agent_smoke.py
        # directly, not run_test.py), so no test_args are built.
        return ""

    def _build_remote_cmd(self) -> str:
        parts = [
            "python3",
            self.AGENT_SMOKE_PATH,
            "--results-xml",
            self.testresult_filepath,
        ]
        for key, flag in (
            ("stability_window", "--stability-window"),
            ("startup_timeout", "--startup-timeout"),
            ("expected_hw_agents", "--expected-hw-agents"),
            ("services", "--services"),
        ):
            value = self.tc.get(key)
            if value is not None and value != "":
                parts += [flag, str(value)]
        return shlex.join(parts)

    def _run_test_impl(self, test_context, skip_tr_xml=False):
        logger.info("Running agent smoke test")

        cmd = f"sudo rm -f {self.testlog_filepath} {self.testresult_filepath}"
        exit_status, output = self.ssh_client.run_cmd(cmd)
        if exit_status != 0:
            logger.error("Failed to clear remote files: %s %s", cmd, output)
            return False

        remote = self._build_remote_cmd()
        cmd = f"sudo {remote} > {self.testlog_filepath} 2>&1"
        logger.info("Running remote command: %s", cmd)
        smoke_status, output = self.ssh_client.run_cmd(cmd)
        logger.debug("smoke exit_status %s output %s", smoke_status, output)

        for remote_path, local_path in (
            (self.testlog_filepath, "/tmp/test.log"),
            (self.testresult_filepath, "/tmp/tr.xml"),
        ):
            exit_status, output = self.scp_client.get_file(remote_path, local_path)
            if exit_status != 0:
                logger.error("Failed to fetch %s: %s", remote_path, output)
                return False

        if smoke_status != 0:
            logger.error("agent_smoke.py exited %s; see /tmp/tr.xml", smoke_status)
            return False
        return True


class Fboss2IntegrationTestRunner(BaseHwTestRunner):
    """Runner for fboss2 CLI integration tests.

    fboss2_integration_test is a gtest binary that drives fboss2-dev CLI
    commands against a running FBOSS instance and verifies their output. It
    is SAI/platform-independent — it talks to the agent over Thrift — so
    unlike the SAI/agent runners it needs no --config or per-model
    known-bad-test key. run_test.py's fboss2_integration subcommand resolves
    both internally (/etc/coop/agent.conf and the bundled
    fboss2_integration_known_bad_tests file).
    """

    # fboss2_integration_test ships in the forwarding test tarball
    # (FORWARDING_TEST_BINARIES) alongside its known-bad-tests file
    # (FORWARDING_TEST_EXTRA) — see fboss/oss/scripts/package.py. run_test.py,
    # fboss2-dev and setup_fboss_env come from the production forwarding image
    # already on the DUT, so (like the other forwarding runners) they're not
    # listed here.
    STACK = _STACK_FORWARDING
    BINARIES = ("bin/fboss2_integration_test",)
    REQUIRED_PATHS = (*BINARIES, *_STACK_SHARE[STACK])

    def test_args(self, model: str) -> str:
        return "fboss2_integration"

    def pre_test(self):
        """No-op: run_test.py fboss2_integration owns the agent lifecycle.

        The fboss2_integration subcommand detects whether production
        multi-switch agents are already running, snapshots their config, and
        cold-boots both agents per test (restoring on teardown). The base
        class warm-boot-state wipe would race with that prod-agent detection,
        so we deliberately skip it here.
        """


class BenchmarkTestRunner(BaseHwTestRunner):
    """Runner for benchmark tests. """

    STACK = _STACK_FORWARDING
    BINARIES = ("bin/sai_all_benchmarks-sai_impl",)
    # hw_bench_configs is not in _STACK_SHARE: this is the only runner that reads
    # it, and a REQUIRED_PATHS entry resolving to nothing is fatal
    # (_slice_members raises), so listing it stack-wide would fail every
    # forwarding runner's deploy against a tarball predating its addition to
    # package.py's FORWARDING_TEST_EXTRA. It must ship alongside hw_test_configs
    # (from _STACK_SHARE): platforms with no benchmark-specific config have a
    # symlink into ../hw_test_configs there.
    REQUIRED_PATHS = (*BINARIES, *_STACK_SHARE[STACK], "share/hw_bench_configs/")

    def test_args(self, model: str) -> str:
        config_name = _SAI_AGENT_CONFIG_NAME.get(model, model)
        logger.info("model=%s hw_bench_config=%s", model, config_name)
        return f"benchmark --config ./share/hw_bench_configs/{config_name}.agent.materialized_JSON{_benchmark_skip_known_bad(model)}"

    # Benchmark binaries spin up their own agent (binds thrift port 5909, owns
    # the ASIC), so the production agents must be down first or the bind aborts
    # (Address already in use) and the ASIC contends (SIGBUS/SIGSEGV). run_test.py
    # stops these for the gtest runners but not for the benchmark sub-command.
    BENCHMARK_DISABLE_SERVICES = ["fboss_sw_agent", "fboss_hw_agent@0"]

    def pre_test(self):
        services = " ".join(self.BENCHMARK_DISABLE_SERVICES)
        logger.info("Stopping production agents for benchmark: %s", services)
        self.ssh_client.run_cmd(f"sudo systemctl mask {services}")
        self.ssh_client.run_cmd(f"sudo systemctl stop {services}")
        time.sleep(2)
        # Agents write can_warm_boot on graceful exit; base wipe forces cold boot.
        super().pre_test()

    def post_test(self):
        services = " ".join(self.BENCHMARK_DISABLE_SERVICES)
        logger.info("Restarting production agents: %s", services)
        self.ssh_client.run_cmd(f"sudo systemctl unmask {services}")
        self.ssh_client.run_cmd(f"sudo systemctl start {services}")

    def binary_exit_is_fatal(self, exit_status: int) -> bool:
        # run_test.py exits non-zero when any individual benchmark fails; that is
        # a test result (captured per-benchmark in the CSV / tr.xml), not an infra
        # error. Only treat the run as infra-fatal if no results CSV was written.
        return self._get_result_csv_name("/tmp/test.log") is None

    def _get_result_csv_name(self, local_log_path: str) -> str | None:
        """Extract CSV filename from benchmark log"""
        with open(local_log_path, encoding="utf-8") as f:
            content = f.read()

        match = re.search(
            r"Benchmark results written to: (benchmark_results_\S+\.csv)", content
        )
        if match:
            return match.group(1)

        logger.warning(
            f"Could not find benchmark results CSV filename in {local_log_path}"
        )
        return None

    def _get_skipped_bm_count(self, local_log_path: str) -> int:
        """Extract num tests skipped from benchmark log"""
        with open(local_log_path, encoding="utf-8") as f:
            for line in f:
                match = re.search(r"Skipped \(known bad, pre-filtered\): (\d+)", line)
                if match:
                    return int(match.group(1))

        logger.warning(f"Could not find skipped count in {local_log_path}")
        return 0

    def _generate_tr_xml_from_csv(
        self, csv_path: str, xml_path: str, csv_timestamp: str, skipped_count: int = 0
    ) -> bool:
        """
        Convert a benchmark CSV into a minimal JUnit-style tr.xml.

        Args:
            csv_path: Path to benchmark_results_*.csv
            xml_path: Output XML path (e.g. /tmp/tr.xml)
            timestamp: timestamp on the original CSV

        Returns:
            bool: if tr.xml creation was successful
        """

        # Convert original CSV timestamp to correct format
        suite_timestamp = datetime.strptime(csv_timestamp, "%Y%m%d_%H%M%S").strftime(
            "%Y-%m-%dT%H:%M:%S.%f"
        )[:-3]

        # Create XML tree
        testsuites_el = ET.Element("testsuites")
        testsuite_el = ET.SubElement(
            testsuites_el,
            "testsuite",
            {
                "tests": "0",  # filled later
                "failures": "0",  # filled later
                "disabled": "0",  # cannot be inferred from CSV
                "errors": "0",  # cannot be inferred from CSV
                "skipped": str(skipped_count),
                "time": "0.000",  # filled later
                "timestamp": suite_timestamp,
                "name": "AllTests",
            },
        )

        # Calculate stats that require row-by-row inspection
        total_failures = 0
        total_time_sec = 0.0

        with open(csv_path, mode="r") as f:
            rows = list(csv.DictReader(f))

        logger.info("Parsing CSV file...")

        for row in rows:
            # Benchmark names aren't structured as ClassName.testName
            name = row.get("benchmark_test_name")
            classname = "Benchmarks"
            # No obvious way to get the actual source file name;
            # using compiled binary as placeholder
            filename = row.get("benchmark_binary_name")

            # Benchmark time is in picoseconds; convert to seconds
            benchmark_time_ps = row.get("benchmark_time_ps", "")
            try:
                case_time_sec = (
                    max(float(benchmark_time_ps) / 1e12, 0.0)
                    if benchmark_time_ps
                    else 0.0
                )
            except (TypeError, ValueError):
                case_time_sec = 0.0
            total_time_sec += case_time_sec

            # Get benchmark results
            test_status = (row.get("test_status") or "").upper()
            threshold_status = (row.get("threshold_status") or "").upper()
            threshold_details = row.get("threshold_details") or ""

            # Add testcase element
            testcase_el = ET.SubElement(
                testsuite_el,
                "testcase",
                {
                    "name": name,
                    "file": filename,
                    "line": "",
                    "status": "run",
                    "result": "timed-out"
                    if (test_status == "TIMEOUT")
                    else "completed",
                    "time": f"{case_time_sec:.6f}",
                    "timestamp": suite_timestamp,  # Per-test timestamp not in CSV
                    "classname": classname,
                },
            )

            # Add failure subelement if appropriate
            failure_reasons = []

            if test_status == "FAILED":
                failure_reasons.append("test_status=FAILED")
            elif test_status == "TIMEOUT":
                failure_reasons.append("test_status=TIMEOUT")

            if threshold_status == "EXCEEDED":
                if threshold_details:
                    failure_reasons.append(f"threshold exceeded: {threshold_details}")
                else:
                    failure_reasons.append("threshold exceeded")

            if failure_reasons:
                total_failures += 1
                message = "; ".join(failure_reasons)

                failure_el = ET.SubElement(
                    testcase_el,
                    "failure",
                    {"message": message},
                )

        total_tests = len(rows) + skipped_count

        testsuite_el.set("tests", str(total_tests))
        testsuite_el.set("failures", str(total_failures))
        testsuite_el.set("time", f"{total_time_sec:.6f}")

        logger.info("Successfully parsed CSV --> writing results to xml file")

        tree = ET.ElementTree(testsuites_el)
        ET.indent(tree, space=" ", level=0)
        tree.write(xml_path, encoding="UTF-8", xml_declaration=True)
        return True

    def _run_test_impl(self, test_context, skip_tr_xml=False) -> bool:
        """
        Run the benchmark test on the DUT.
        This acts as a wrapper around the base class implementation and adds
        additional functionality for generating a tr.xml based on a
        benchmark_result.csv, as benchmarks do not produce a tr.xml
        automatically. (setup()/deploy and the deploy-only gate already ran in
        run_test(); the base run always skips its own tr.xml fetch here.)
        """
        success = super()._run_test_impl(test_context, skip_tr_xml=True)
        if not success:
            return False

        # Benchmarks do not produce tr.xml, only a CSV file
        csv_filename = self._get_result_csv_name("/tmp/test.log")
        if csv_filename is None:
            logger.error("Failed to find benchmark results CSV filename in test log")
            return False

        self.testresult_filepath = f"/opt/fboss/{csv_filename}"
        local_csv_path = "/tmp/benchmark_results.csv"
        exit_status, output = self.scp_client.get_file(
            self.testresult_filepath, local_csv_path
        )
        if exit_status != 0:
            logger.warning("Failed to fetch test results: %s", output)

        # Use CSV file to create tr.xml locally
        # CSV filename looks like:
        # f"benchmark_results_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"
        csv_timestamp = csv_filename.replace("benchmark_results_", "").replace(
            ".csv", ""
        )
        skipped_count = self._get_skipped_bm_count("/tmp/test.log")

        logger.info("Generating /tmp/tr.xml from %s", local_csv_path)
        success = self._generate_tr_xml_from_csv(
            local_csv_path, "/tmp/tr.xml", csv_timestamp, skipped_count
        )
        if not success:
            logger.error("Failed to generate /tmp/tr.xml from %s", local_csv_path)
            return False

        self.normalize_test_results_file()

        return True


class QsfpBenchmarkTestRunner(BenchmarkTestRunner):
    """Runner for QSFP benchmarks (run_test.py benchmark --qsfp)."""

    STACK = _STACK_FORWARDING
    BINARIES = ("bin/qsfp_hw_test_benchmark",)
    REQUIRED_PATHS = (*BINARIES, *_STACK_SHARE[STACK])

    # Binary must own the xcvr i2c bus, same as qsfp_hw_test (TEST_DISABLE_SERVICES).
    BENCHMARK_DISABLE_SERVICES = ["qsfp_service", "led_service"]

    def test_args(self, model: str) -> str:
        config_name = _LINK_QSFP_TEST_CONFIG_NAME.get(model, model)
        logger.info("model=%s qsfp_test_config=%s", model, config_name)
        return (
            f"benchmark --qsfp"
            f" --qsfp-config ./share/qsfp_test_configs/{config_name}.materialized_JSON"
            f" --skip-known-bad-tests {config_name}/{_QSFP_BENCH_PHY_SDK}"
        )
