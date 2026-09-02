"""Artifact deploy engine: fetch/pack this runner's test-binary slice and ship
it to the DUT, with a host extract cache and content-addressed DUT markers.

Transport (SSH/SCP clients) is injected, and nothing here depends on the other
test_runner modules — this file plus junit.py form the generic core a future
shared package could lift out (see README.md).
"""

import hashlib
import logging
import os
import shutil
import subprocess
import tarfile
from pathlib import Path

logger = logging.getLogger("test_runner")

# Env the orchestrator (TestInstanceFboss._resolve_artifact_urls) sets.  The
# orchestrator owns *what* to use — it resolves the Nexis tarball URLs (from a
# build_id) or discovers the locally-built CMake build dir(s) — and the runner
# just consumes what it's handed for its STACK: a tarball URL (fetch + extract)
# or a local build/fboss dir (pack from binaries + repo configs).
_ENV_BUILD_ID = "FBOSS_BUILD_ID"
STACK_FORWARDING = "forwarding"
STACK_PLATFORM = "platform"
# Per-stack env: a Nexis CloudStack tarball URL, or a local build/fboss dir.
_ENV_TARBALL_URL = {
    STACK_FORWARDING: "FBOSS_FORWARDING_TARBALL_URL",
    STACK_PLATFORM: "FBOSS_PLATFORM_TARBALL_URL",
}
_ENV_LOCAL_DIR = {
    STACK_FORWARDING: "FBOSS_FORWARDING_LOCAL_DIR",
    STACK_PLATFORM: "FBOSS_PLATFORM_LOCAL_DIR",
}

# Per-stack share/ shipped to every runner on that stack. Forwarding tests read
# these configs (--config, --skip-known-bad-tests, --enable-production-features);
# they all live in the forwarding test tarball (package.py FORWARDING_TEST_EXTRA)
# and in the repo, so they resolve on both the Nexis and local paths. Platform
# tests read no share/ configs (run_test.py drives them by --type), so that set
# is empty. The forwarding tree is ~19 MB vs ~1 GB per test binary, so we ship
# all of it rather than a per-runner subset that can silently miss a file — only
# the binaries are worth slicing per runner (see each runner's BINARIES).
STACK_SHARE: dict[str, tuple[str, ...]] = {
    STACK_FORWARDING: (
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
    STACK_PLATFORM: (),
}

# Deploy-only mode: when set to "1" (by nhtests-run --mode deploy), run_test()
# performs setup()/deploy to push this runner's slice onto the DUT, then
# returns without executing the test on the DUT. Contract is an explicit
# "1" (not mere presence) so a stray FBOSS_DEPLOY_ONLY=0/false can't silently
# skip execution.
ENV_DEPLOY_ONLY = "FBOSS_DEPLOY_ONLY"
ENV_DEPLOY_ONLY_ON = "1"

FBOSS_ROOT_ON_DUT = "/opt/fboss"


# Two caches amortize two different costs (see ArtifactDeployer.deploy).
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
_DUT_MARKER_DIR = f"{FBOSS_ROOT_ON_DUT}/.deployed"


class ArtifactDeployer:
    """Deploys one runner's test-binary slice onto the DUT.

    Constructed per deploy with the runner's identity (name, stack, manifest)
    and the SSH/SCP transport to use.
    """

    def __init__(self, runner_name, stack, required_paths, ssh_client, scp_client):
        self.runner_name = runner_name
        self.stack = stack
        self.required_paths = required_paths
        self.ssh_client = ssh_client
        self.scp_client = scp_client

    def deploy(self) -> None:
        """Deploy this runner's test binary slice onto the DUT."""
        # The orchestrator hands us, for this runner's stack, either a local
        # build/fboss dir (preferred when present) or a Nexis tarball URL.
        local_dir = os.environ.get(_ENV_LOCAL_DIR[self.stack])
        url = os.environ.get(_ENV_TARBALL_URL[self.stack])
        if local_dir:
            namespace = f"local-{self._local_build_fingerprint(local_dir)}"
        elif url:
            # Nexis build: FBOSS_BUILD_ID is the cache/marker namespace.
            namespace = os.environ.get(_ENV_BUILD_ID)
            if not namespace:
                raise RuntimeError(
                    f"{self.runner_name}: {_ENV_TARBALL_URL[self.stack]} is set but "
                    f"{_ENV_BUILD_ID} is not — the Nexis cache namespace is required."
                )
        else:
            raise RuntimeError(
                f"{self.runner_name} requires {_ENV_LOCAL_DIR[self.stack]} (local build) "
                f"or {_ENV_TARBALL_URL[self.stack]} (Nexis tarball URL).  The "
                "orchestrator (nhtests-run) sets these; pass --test-build-id or "
                "build the FBOSS stack locally."
            )

        # Bound the host cache to this single namespace — drop any other
        # build's cached contents so it can't accumulate over time.
        self._prune_stale_cache(namespace)

        # Resolve this runner's required_paths to (source, archive-path) pairs.
        # Local sources are read straight from the build dir + repo; a Nexis build
        # is downloaded+extracted (and cached) first, then sliced out of that tree.
        if local_dir:
            members = self._slice_members(
                lambda rel: self._local_source_path(rel, local_dir)
            )
        else:
            extract_dir = self._ensure_extract_cached(url, namespace)
            members = self._slice_members(lambda rel: os.path.join(extract_dir, rel))

        slice_tar = self._pack_slice(members, namespace)
        try:
            slice_sha = self._sha256(slice_tar)
            if self._is_slice_on_dut(slice_sha):
                logger.info(
                    "%s slice already on DUT (sha %s); skipping deploy",
                    self.runner_name, slice_sha[:12],
                )
                return
            self._deploy_slice_to_dut(slice_tar, slice_sha)
        finally:
            Path(slice_tar).unlink(missing_ok=True)

    @staticmethod
    def _fboss_repo_root() -> Path:
        """The fboss repo root (this file is at <root>/tests/libs/test_runner/)."""
        return Path(__file__).resolve().parents[3]

    def _local_build_fingerprint(self, build_fboss_dir: str) -> str:
        """Stable per-build id for this runner's local CMake slice. """
        h = hashlib.sha256()
        for rel in self.required_paths:
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
        """Resolve required_paths to (source_path, archive_name) pairs to pack.

        ``resolve(rel)`` maps a required_paths entry (trailing "/" stripped) to its
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
        for rel in self.required_paths:
            rel_clean = rel.rstrip("/")
            src = resolve(rel_clean)
            if os.path.exists(src):
                members.append((src, rel_clean))
            else:
                missing.append(rel)
        if missing:
            raise RuntimeError(
                f"{self.runner_name} REQUIRED_PATHS not found: {missing}.  Either "
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
            f"{self.runner_name}: don't know the local source for REQUIRED_PATH "
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

    def _is_slice_on_dut(self, slice_sha: str) -> bool:
        """True if the DUT already holds this runner's slice with the same content."""
        marker = f"{_DUT_MARKER_DIR}/{self.runner_name}.sha"
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

    def _pack_slice(self, members: list[tuple[str, str]], namespace: str) -> str:
        """Pack this runner's slice into a tar to ship to the DUT.

        Adds each (source, archive_name) pair straight into the archive, reading
        the files in place from the local build dir / repo (or the extracted Nexis
        tree) — no staging copy is needed to line the on-DUT paths up.  Directories
        (share/) are added recursively, and tarfile carries each file's mode, so
        the exec bit on binaries survives.
        """
        slice_tar = f"{_HOST_CACHE_ROOT}/{namespace}/{self.runner_name}-slice.tar"
        os.makedirs(os.path.dirname(slice_tar), exist_ok=True)
        logger.info(
            "Packing slice tar: runner=%s members=%d", self.runner_name, len(members)
        )
        # "w" truncates, so a leftover from a previous failed run is harmless.
        with tarfile.open(slice_tar, "w") as tar:
            for src, arcname in members:
                tar.add(src, arcname=arcname)
        return slice_tar

    def _deploy_slice_to_dut(self, slice_tar: str, slice_sha: str) -> None:
        """SCP the slice tar, extract into /opt/fboss, then record its sha.

        Extract + sha-write are chained with `&&` so the marker can only hold a
        sha once the extract succeeded.  Cleanup of the slice tar on the DUT
        runs in `finally` regardless of outcome.
        """
        remote_slice = f"/tmp/fboss-{self.runner_name}-slice.tar"
        marker = f"{_DUT_MARKER_DIR}/{self.runner_name}.sha"
        try:
            logger.info("Copying slice tar to DUT at %s", remote_slice)
            exit_status, output = self.scp_client.put_file(slice_tar, remote_slice)
            if exit_status != 0:
                raise RuntimeError(
                    f"Failed to copy slice tar for {self.runner_name} to DUT: {output}"
                )

            logger.info(
                "Extracting slice tar on DUT into %s and recording sha %s",
                FBOSS_ROOT_ON_DUT, slice_sha[:12],
            )
            exit_status, output = self.ssh_client.run_cmd(
                f"sudo mkdir -p {_DUT_MARKER_DIR} && "
                f"sudo tar -C {FBOSS_ROOT_ON_DUT} -xf {remote_slice} && "
                f"echo {slice_sha} | sudo tee {marker} > /dev/null"
            )
            if exit_status != 0:
                raise RuntimeError(
                    f"Failed to extract slice tar for {self.runner_name} on DUT: {output}"
                )
        finally:
            cleanup_status, cleanup_output = self.ssh_client.run_cmd(
                f"sudo rm -f {remote_slice}"
            )
            if cleanup_status != 0:
                logger.warning(
                    "Failed to clean up slice tar on DUT: %s", cleanup_output
                )

        logger.info("Deployed %s test artifacts to DUT", self.runner_name)

    def _fetch(self, url: str, dest_path: str) -> None:
        """Fetch a Nexis tarball to dest_path on the runner host.

        Always a CloudStack HTTP(S) URL (the orchestrator only ever resolves
        *_TARBALL_URL to one); fetched with wget for parity with the prepare-side
        artifact fetch — same retry / redirect semantics, same CloudStack-friendly
        defaults.  Local builds never reach here: they're handed a *_LOCAL_DIR and
        packed straight from disk (see deploy / _pack_slice).
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
