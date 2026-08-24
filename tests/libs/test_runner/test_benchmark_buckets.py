"""Unit tests for the split benchmark buckets.

Each module under tests/agent_hw/benchmarks/ selects one benchmark family via
test_context["filters"]; rest_benchmarks.py derives whatever the others do not
claim. These drive the real BenchmarkFramework grammar rather than a
reimplementation, so the filters are checked against the code that interprets
them on the DUT. The authoritative name list comes from the binary (--bm_list),
so representative names are used here and the partition is re-checked per bucket
during DUT validation.
"""

import sys
from argparse import Namespace
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from tests.libs.test_runner.filter_utils import (
    catch_all_filters,
    load_test_context,
    module_inclusion_filters,
)
from tests.libs.test_runner.runner import (
    _repo_dir,
    _SAI_AGENT_CONFIG_NAME,
    _SAI_KNOWN_BAD_KEY,
    BenchmarkTestRunner,
    QsfpBenchmarkTestRunner,
)

_BENCH_DIR = _repo_dir(Path("tests/agent_hw/benchmarks"))

# The framework is shipped from the DUT image, not this package, so it is not on
# the path by default.
sys.path.insert(0, str(_repo_dir(Path("fboss/oss/scripts/run_scripts"))))

from fboss_test_runner.frameworks.benchmark_framework import (  # noqa: E402
    BenchmarkFramework,
)

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


def _select(filters, names=_NAMES, tmp_path=None):
    """Run `filters` through set_filters' file format and the real grammar."""
    path = (tmp_path or Path("/tmp")) / "tests.conf"
    path.write_text("".join(f"{f}\n" for f in filters))
    framework = BenchmarkFramework.__new__(BenchmarkFramework)
    args = Namespace(filter=None, filter_file=str(path), profile=None)
    return framework._get_benchmarks_to_run(names, args) or []


def _bucket_modules():
    return sorted(
        p for p in _BENCH_DIR.iterdir() if p.suffix == ".py" and p.name != "__init__.py"
    )


def _bucket_filters(path):
    """The full filters list, exclusions included -- what the runner writes."""
    return load_test_context(str(path))["filters"]


# ---- runner plumbing -----------------------------------------------------


@pytest.mark.parametrize("runner_cls", (BenchmarkTestRunner, QsfpBenchmarkTestRunner))
def test_build_test_cmd_passes_filter_file(runner_cls):
    runner = runner_cls()
    runner.tc = {"model": "nhbw800f", "filters": ["*Stats*"]}
    cmd = runner.build_test_cmd("nhbw800f")
    assert f"--filter_file={runner.filter_filepath}" in cmd


@pytest.mark.parametrize("runner_cls", (BenchmarkTestRunner, QsfpBenchmarkTestRunner))
def test_set_filters_is_inherited(runner_cls, tmp_path):
    # The old override was a no-op returning True without writing anything.
    runner = runner_cls()
    runner.tc = {"filters": ["*Stats*", "-*Voq*"], "gtest_filter": None}
    runner.scp_client = MagicMock()
    runner.scp_client.put_file.return_value = (0, "ok")
    src = tmp_path / "tests.conf"

    assert runner.set_filters(str(src), "/home/netops/tests.conf") is True
    assert src.read_text().splitlines() == ["*Stats*", "-*Voq*"]


@pytest.mark.parametrize(
    ("model", "config_name"),
    [
        ("nhbw800f", "wedge800bact"),  # real benchmark config
        ("minipack3", "montblanc"),  # symlink into hw_test_configs
    ],
)
def test_bench_config_always_from_hw_bench_configs(model, config_name):
    args = BenchmarkTestRunner().test_args(model)
    assert f"./share/hw_bench_configs/{config_name}.agent.materialized_JSON" in args
    assert "hw_test_configs" not in args


def test_benchmark_runner_pins_multi_switch(monkeypatch):
    monkeypatch.setenv("FBOSS_AGENT_RUN_MODE", "mono")

    args = BenchmarkTestRunner().test_args("nhbw800f")

    assert "benchmark --agent-run-mode multi_switch" in args
    assert "benchmark --agent-run-mode mono" not in args


def test_bench_config_exists_for_every_benchmarked_platform():
    """test_args() names hw_bench_configs unconditionally, so a platform without
    an entry there (real config or symlink) would fail on the DUT."""
    bench_dir = _repo_dir(Path("fboss/oss/hw_bench_configs"))
    models = set(_SAI_KNOWN_BAD_KEY) | set(_SAI_AGENT_CONFIG_NAME)
    missing = sorted(
        name
        for name in (_SAI_AGENT_CONFIG_NAME.get(m, m) for m in models)
        if not (bench_dir / f"{name}.agent.materialized_JSON").is_file()
    )
    assert not missing, f"no hw_bench_configs entry (add a symlink): {missing}"


# ---- catch-all derivation ------------------------------------------------


def test_module_inclusion_filters_stops_at_first_exclusion(tmp_path):
    module = tmp_path / "bucket.py"
    module.write_text('test_context = {"filters": ["*A*", "*B*", "-*C*", "*D*"]}\n')
    assert module_inclusion_filters(str(module)) == ["*A*", "*B*"]


def test_catch_all_filters_inverts_siblings(tmp_path):
    (tmp_path / "one.py").write_text('test_context = {"filters": ["*A*", "-*Z*"]}\n')
    (tmp_path / "two.py").write_text('test_context = {"filters": ["*B*"]}\n')
    rest = tmp_path / "rest.py"
    rest.write_text("")

    # Only the first exclusion carries the "-"; sibling exclusions are not
    # inherited, so "*Z*" must not appear.
    assert catch_all_filters(str(rest), str(tmp_path)) == ["*", "-*A*", "*B*"]


def test_catch_all_filters_dedupes_and_skips_self(tmp_path):
    (tmp_path / "one.py").write_text('test_context = {"filters": ["*A*"]}\n')
    (tmp_path / "two.py").write_text('test_context = {"filters": ["*A*", "*B*"]}\n')
    rest = tmp_path / "rest.py"
    rest.write_text('test_context = {"filters": ["*NeverExcluded*"]}\n')

    assert catch_all_filters(str(rest), str(tmp_path)) == ["*", "-*A*", "*B*"]


# ---- the real buckets ----------------------------------------------------


def test_every_bucket_selects_something(tmp_path):
    for path in _bucket_modules():
        assert _select(_bucket_filters(path), tmp_path=tmp_path), path.name


def test_buckets_partition_benchmarks(tmp_path):
    owners = {}
    for path in _bucket_modules():
        for name in _select(_bucket_filters(path), tmp_path=tmp_path):
            owners.setdefault(name, []).append(path.name)

    assert {n: o for n, o in owners.items() if len(o) > 1} == {}, "overlapping buckets"
    assert sorted(owners) == sorted(_NAMES), "benchmarks claimed by no bucket"


def test_voq_bucket_owns_voq_variants(tmp_path):
    # A name carrying both a family word and Voq belongs here, not in the family
    # bucket -- what the "-*Voq*" exclusions elsewhere are for.
    selected = _select(
        _bucket_filters(_BENCH_DIR / "voq_fabric_benchmarks.py"), tmp_path=tmp_path
    )
    assert "HwVoqStatsCollection" in selected
    assert "HwInitAndExitVoqBenchmark" in selected
    assert "HwSwitchReachabilityChangeVoqBenchmark" in selected


def test_rest_bucket_owns_the_leftovers(tmp_path):
    selected = _select(
        _bucket_filters(_BENCH_DIR / "rest_benchmarks.py"), tmp_path=tmp_path
    )
    assert sorted(selected) == ["RibSyncFibBenchmark", "cpuLatencyBenchmark"]


def test_qsfp_benchmark_test_still_selects_everything(tmp_path):
    qsfp_test = _repo_dir(Path("tests/qsfp")) / "qsfp_benchmark_tests.py"
    filters = load_test_context(str(qsfp_test))["filters"]
    assert _select(filters, tmp_path=tmp_path) == _NAMES
