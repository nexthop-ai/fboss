"""Drift guards: checks that read the repo rather than the library.

Every runner's BINARIES must name something the upstream on-DUT runner execs,
every benchmarked platform needs a hw_bench_configs entry, the benchmark
bucket modules under tests/agent_hw/benchmarks/ must partition the benchmark
names, every shipped link/qsfp variant wrapper must name a variant some
platform can run, and fboss_init.sh's variant flag must agree with the
platform descriptors. These are the only tests in the package that need the
repo trees in runfiles.
"""

import json
import re
import subprocess
import sys
from argparse import Namespace
from pathlib import Path

import pytest

from tests.libs.test_runner import (
    BenchmarkTestRunner,
    BspTestRunner,
    LinkTestRunner,
    PlatformTestRunner,
    QsfpBenchmarkTestRunner,
    QsfpTestRunner,
    SaiAgentTestRunner,
    SaiTestRunner,
)
from tests.libs.test_runner.base import BaseHwTestRunner
from tests.libs.test_runner.deploy import STACK_FORWARDING, STACK_PLATFORM, STACK_SHARE
from tests.libs.test_runner.filter_utils import load_test_context
from tests.libs.test_runner.platform_configs import (
    LINK_QSFP_TEST_CONFIG_NAME,
    SAI_AGENT_CONFIG_NAME,
    SAI_KNOWN_BAD_KEY,
)
from tests.libs.test_runner.platform_mapping import repo_dir
from tests.libs.test_runner.variants import derive_variant_chain, load_full_platform_mapping

_BENCH_DIR = repo_dir(Path("tests/agent_hw/benchmarks"))

_RUN_SCRIPTS = repo_dir(Path("fboss/oss/scripts/run_scripts"))


@pytest.fixture(scope="module")
def benchmark_framework():
    """The on-DUT BenchmarkFramework class. It ships in the DUT image, not this
    package, so it is imported from the run_scripts tree on demand."""
    sys.path.insert(0, str(_RUN_SCRIPTS))
    try:
        from fboss_test_runner.frameworks.benchmark_framework import BenchmarkFramework
    finally:
        sys.path.remove(str(_RUN_SCRIPTS))
    return BenchmarkFramework


class TestRunnerManifests:
    def test_sai_agent_runner_ships_production_features(self):
        assert "share/production_features/" in SaiAgentTestRunner.REQUIRED_PATHS

    def test_platform_runner_relies_on_image_for_run_test_py(self):
        # run_test.py + setup_fboss_env come from the production image on the DUT
        # (like the forwarding runners and BspTestRunner), so they aren't shipped.
        assert "bin/run_test.py" not in PlatformTestRunner.REQUIRED_PATHS

    def test_bsp_runner_does_not_need_run_test_py(self):
        assert "bin/run_test.py" not in BspTestRunner.REQUIRED_PATHS

    def test_benchmark_runner_has_a_deploy_manifest(self):
        assert BenchmarkTestRunner.STACK == STACK_FORWARDING
        assert "bin/sai_all_benchmarks-sai_impl" in BenchmarkTestRunner.REQUIRED_PATHS

    def test_only_benchmark_runner_ships_hw_bench_configs(self):
        # test_args() reads it, and its entries for platforms without a
        # benchmark-specific config are symlinks into ../hw_test_configs, so both
        # dirs must ship. No other runner needs it.
        for rel in ("share/hw_bench_configs/", "share/hw_test_configs/"):
            assert rel in BenchmarkTestRunner.REQUIRED_PATHS
        assert "share/hw_bench_configs/" not in STACK_SHARE[STACK_FORWARDING]
        for cls in (SaiTestRunner, SaiAgentTestRunner, QsfpTestRunner, LinkTestRunner):
            assert "share/hw_bench_configs/" not in cls.REQUIRED_PATHS

    def test_qsfp_benchmark_runner_has_a_deploy_manifest(self):
        assert QsfpBenchmarkTestRunner.STACK == STACK_FORWARDING
        assert "bin/qsfp_hw_test_benchmark" in QsfpBenchmarkTestRunner.REQUIRED_PATHS
        # Must not inherit the SAI benchmark binary slice.
        assert "bin/sai_all_benchmarks-sai_impl" not in QsfpBenchmarkTestRunner.REQUIRED_PATHS
        # QSFP benchmarks read qsfp_test_configs, not hw_bench_configs.
        assert "share/hw_bench_configs/" not in QsfpBenchmarkTestRunner.REQUIRED_PATHS

    def test_forwarding_runners_route_to_forwarding_stack(self):
        for cls in (SaiTestRunner, SaiAgentTestRunner, BenchmarkTestRunner, QsfpBenchmarkTestRunner):
            assert cls.STACK == STACK_FORWARDING, f"{cls.__name__} should be forwarding"

    def test_platform_stack_runners_route_to_platform_stack(self):
        for cls in (PlatformTestRunner, BspTestRunner):
            assert cls.STACK == STACK_PLATFORM, f"{cls.__name__} should be platform"


# run scripts and python smoke scripts ship under bin/ but aren't run_test.py
# gtest binaries, so they're excluded from the binary cross-check below.
_NON_BINARY_BIN = ("run_test.py", "setup_fboss_env")


def _declared_test_binaries(cls):
    """The run_test.py gtest binaries a runner deploys (bin/<name>), excluding
    run scripts (run_test.py/setup_fboss_env) and the python smoke scripts."""
    names = []
    for path in getattr(cls, "REQUIRED_PATHS", ()):
        if not path.startswith("bin/"):
            continue
        name = path[len("bin/"):]
        if name.endswith(".py") or name in _NON_BINARY_BIN:
            continue
        names.append(name)
    return names


def test_runner_binaries_are_known_to_fboss_test_runner():
    """Every gtest binary a runner deploys must be one the upstream test runner
    actually execs.

    The on-DUT runner is the upstream ``fboss_test_runner`` package (its
    ``runners/*.py`` _get_test_binary_name methods + ``constants.py``); it is the
    source of truth for binary names. Our per-runner BINARIES mirror that, so
    this guards against drift: a stale or mistyped binary name here, or upstream
    renaming/removing one, fails loudly with a pointer to reconcile.
    """
    pkg = _RUN_SCRIPTS / "fboss_test_runner"
    tokens: set[str] = set()
    for py in pkg.rglob("*.py"):
        tokens |= set(re.findall(r"[A-Za-z0-9_.\-]+", py.read_text()))

    def _all_subclasses(cls):
        for sub in cls.__subclasses__():
            yield sub
            yield from _all_subclasses(sub)

    for cls in _all_subclasses(BaseHwTestRunner):
        for name in _declared_test_binaries(cls):
            assert name in tokens, (
                f"{cls.__name__} deploys bin/{name}, but the upstream "
                f"fboss_test_runner package never references it. Reconcile the "
                f"runner's BINARIES against fboss_test_runner/runners/*.py, "
                f"the source of truth for binary names."
            )


def test_bench_config_exists_for_every_benchmarked_platform():
    """test_args() names hw_bench_configs unconditionally, so a platform without
    an entry there (real config or symlink) would fail on the DUT."""
    bench_dir = repo_dir(Path("fboss/oss/hw_bench_configs"))
    models = set(SAI_KNOWN_BAD_KEY) | set(SAI_AGENT_CONFIG_NAME)
    missing = sorted(
        name
        for name in (SAI_AGENT_CONFIG_NAME.get(m, m) for m in models)
        if not (bench_dir / f"{name}.agent.materialized_JSON").is_file()
    )
    assert not missing, f"no hw_bench_configs entry (add a symlink): {missing}"


# ---- benchmark buckets ------------------------------------------------------
#
# Each module under tests/agent_hw/benchmarks/ selects one benchmark family via
# test_context["filters"]; rest_benchmarks.py derives whatever the others do not
# claim. These drive the real BenchmarkFramework grammar rather than a
# reimplementation, so the filters are checked against the code that interprets
# them on the DUT. The authoritative name list comes from the binary (--bm_list),
# so representative names are used here and the partition is re-checked per bucket
# during DUT validation.

_NAMES = [
    "HwFswScaleRouteAddBenchmark",
    "HwFswScaleRouteDelBenchmark",
    "HwVoqScaleRouteAddBenchmark",
    "HwInitAndExit100Gx100GBenchmark",
    "HwInitAndExitVoqBenchmark",
    "HwStatsCollection",
    "HwVoqStatsCollection",
    "HwClearInterfacePhyCounters",
    "RxSlowPathBenchmark",
    "BgpRxSlowPathRouteChangeBenchmark",
    "HwEcmpGroupShrink",
    "HwUcmp128WidthScaleBenchmark",
    "HwSrv6V6RouteScaleBenchmark",
    "HwSrv6EcmpGroupScaleBenchmark",
    "SystemScaleMemoryBenchmark",
    "HwSwitchReachabilityChangeVoqBenchmark",
    "RibSyncFibBenchmark",
    "cpuLatencyBenchmark",
]


def _select(framework_cls, filters, tmp_path, names=_NAMES):
    """Run `filters` through set_filters' file format and the real grammar."""
    path = tmp_path / "tests.conf"
    path.write_text("".join(f"{f}\n" for f in filters))
    framework = framework_cls.__new__(framework_cls)
    args = Namespace(filter=None, filter_file=str(path), profile=None)
    return framework._get_benchmarks_to_run(names, args) or []


def _bucket_modules():
    return sorted(
        p for p in _BENCH_DIR.iterdir() if p.suffix == ".py" and p.name != "__init__.py"
    )


def _bucket_filters(path):
    """The full filters list, exclusions included -- what the runner writes."""
    return load_test_context(str(path))["filters"]


def test_memory_scale_bucket_declares_timeout():
    ctx = load_test_context(str(_BENCH_DIR / "memory_scale_benchmarks.py"))
    assert ctx["test_run_timeout"] > 1200


def test_every_bucket_selects_something(tmp_path, benchmark_framework):
    for path in _bucket_modules():
        assert _select(benchmark_framework, _bucket_filters(path), tmp_path), path.name


def test_buckets_partition_benchmarks(tmp_path, benchmark_framework):
    owners = {}
    for path in _bucket_modules():
        for name in _select(benchmark_framework, _bucket_filters(path), tmp_path):
            owners.setdefault(name, []).append(path.name)

    assert {n: o for n, o in owners.items() if len(o) > 1} == {}, "overlapping buckets"
    assert sorted(owners) == sorted(_NAMES), "benchmarks claimed by no bucket"


def test_voq_bucket_owns_voq_variants(tmp_path, benchmark_framework):
    # A name carrying both a family word and Voq belongs here, not in the family
    # bucket -- what the "-*Voq*" exclusions elsewhere are for.
    selected = _select(benchmark_framework, _bucket_filters(_BENCH_DIR / "voq_fabric_benchmarks.py"), tmp_path)
    assert "HwVoqStatsCollection" in selected
    assert "HwInitAndExitVoqBenchmark" in selected
    assert "HwSwitchReachabilityChangeVoqBenchmark" in selected


def test_rest_bucket_owns_the_leftovers(tmp_path, benchmark_framework):
    selected = _select(benchmark_framework, _bucket_filters(_BENCH_DIR / "rest_benchmarks.py"), tmp_path)
    assert sorted(selected) == ["RibSyncFibBenchmark", "cpuLatencyBenchmark"]


def test_qsfp_benchmark_test_still_selects_everything(tmp_path, benchmark_framework):
    qsfp_test = repo_dir(Path("tests/qsfp")) / "qsfp_benchmark_tests.py"
    filters = load_test_context(str(qsfp_test))["filters"]
    assert _select(benchmark_framework, filters, tmp_path) == _NAMES


# ---- shipped variant wrappers ----------------------------------------------

# Config names the fleet runs: the explicit overrides plus the models that fall
# through _config_name's identity path.
_FLEET_CONFIG_NAMES = sorted(
    set(LINK_QSFP_TEST_CONFIG_NAME.values())
    | {"nh4220f", "nh4010f", "wedge800bnhp", "wedge800cnhp"}
)


class TestShippedWrappers:
    """Every variant wrapper file must name a variant a real platform can run.

    Checked against the shipped mappings, not fixtures: the failure this guards
    against is chain derivation drifting away from what platforms actually
    offer, which turns every wrapper into a silent SKIP.
    """

    @staticmethod
    def _wrapper_variants():
        return {
            path.name: load_test_context(str(path)).get("variant")
            for directory in ("tests/link", "tests/qsfp")
            for path in sorted(repo_dir(Path(directory)).glob("*_hw_tests_*.py"))
        }

    def test_every_wrapper_variant_is_offered_by_a_shipped_platform(self):
        offered = set()
        for config_name in _FLEET_CONFIG_NAMES:
            offered.update(
                v.name for v in derive_variant_chain(load_full_platform_mapping(config_name))
            )
        assert offered, "no platform mappings readable; check the test's runfiles"
        wrappers = {n: v for n, v in self._wrapper_variants().items() if v}
        assert wrappers, "no variant wrapper files found"
        unrunnable = {name: v for name, v in wrappers.items() if v not in offered}
        assert not unrunnable, f"wrappers no shipped platform can run: {unrunnable}"


# ---- boot-time variant flag -------------------------------------------------


class TestBootScriptMatchesDescriptor:
    """fboss_init.sh composes the variant flag name and the P1 descriptor
    declares it. A divergence fails silently on hardware, since the box just
    takes the default mapping, so pin the two together here."""

    _INIT_SCRIPT = (
        repo_dir(Path("fboss-image/image_builder/templates/centos-09.0/root_files/usr/local/bin"))
        / "fboss_init.sh"
    )
    _PLATFORM_CONFIGS = repo_dir(Path("fboss/configs/platforms"))
    _P1_DESCRIPTOR = (
        _PLATFORM_CONFIGS
        / "nexthop/m4062nhp/variants/m4062nhp_p1/platform_mapping/generated"
        / "platform_descriptor.json"
    )

    def _composed_flag(self, tmp_path, state, substate, respin) -> str:
        script = self._INIT_SCRIPT.read_text()
        start = script.index("get_eeprom_field() {")
        end = script.index("enable_hw_agents() {")
        functions = script[start:end]
        assert "set_variant_flags" in functions

        parsed = tmp_path / "CHASSIS_EEPROM_PARSED"
        parsed.write_text(
            f"Production State: {state}\n"
            f"Production Sub-State: {substate}\n"
            f"Re-Spin/Variant Indicator: {respin}\n"
        )
        flagfile = tmp_path / "variant_flags"
        subprocess.run(
            [
                "bash",
                "-c",
                f"log(){{ :; }}; error(){{ :; }}\n"
                f"CHASSIS_EEPROM_PARSED={parsed}\nVARIANT_FLAGFILE={flagfile}\n"
                f"{functions}\nset -e\nset_variant_flags",
            ],
            check=True,
        )
        return flagfile.read_text().strip() if flagfile.exists() else ""

    def _declared_attributes(self) -> set[str]:
        declared = set()
        for path in self._PLATFORM_CONFIGS.rglob("platform_descriptor.json"):
            declared |= set(json.loads(path.read_text()).get("variantAttributes", {}))
        return declared

    def test_p1_flag_is_what_the_p1_descriptor_declares(self, tmp_path, benchmark_framework):
        declared = json.loads(self._P1_DESCRIPTOR.read_text())["variantAttributes"]
        assert len(declared) == 1
        assert self._composed_flag(tmp_path, 1, 1, 0) == f"--{next(iter(declared))}=true"

    def test_p2_flag_is_claimed_by_no_descriptor(self, tmp_path, benchmark_framework):
        flag = self._composed_flag(tmp_path, 2, 2, 0)
        assert flag == "--hwrev_state2_substate2_respin0=true"
        assert flag.removeprefix("--").removesuffix("=true") not in self._declared_attributes()
