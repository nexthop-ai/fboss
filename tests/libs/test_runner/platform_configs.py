"""Per-model FBOSS config knowledge: config codenames, known-bad-test keys,
production-feature keys.
"""

import copy
import re

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
SAI_AGENT_CONFIG_NAME: dict[str, str] = {
    "minipack3": "montblanc",
    "nhbw800f": "wedge800bact",
    "nhcw800f": "wedge800cact",
    "nh4215f": "m4062nhp",
}

# Model → config name override for link/QSFP tests (omit when they match).
LINK_QSFP_TEST_CONFIG_NAME: dict[str, str] = {
    "minipack3": "montblanc",
    "nh4215f": "m4062nhp",
    "nhbw800f": "wedge800bact",
    "nhcw800f": "wedge800cact",
}

# Default CREDO_SDK_VERSION in fboss/lib/phy/CredoSdkVersion.h. qsfp_bench keys
# unsupported_tests on <platform>/<phy_sdk> and matches it exactly.
QSFP_BENCH_PHY_SDK = "credo-0.7.2"

# vendor/coldboot-sai/warmboot-sai/asic — key for run_test.py
# --skip-known-bad-tests against ./share/hw_known_bad_tests/sai*_known_bad_tests.
# Without this, ~128 known-broken tests for tomahawk5 (and the unsupported list)
# run and fail, gutting the pass rate. run_test.py auto-tries the /mono or
# /multi_switch suffix for the sai_agent file, so the same 4-tuple covers both
# SaiTestRunner and SaiAgentTestRunner.
SAI_KNOWN_BAD_KEY: dict[str, str] = {
    "minipack3": "brcm/13.3.0.0_odp/13.3.0.0_odp/tomahawk5",
    "wedge800bact": "brcm/13.3.0.0_odp/13.3.0.0_odp/tomahawk5",
    "nhbw800f": "brcm/13.3.0.0_odp/13.3.0.0_odp/tomahawk5",
    "wedge800cact": "leaba/25.11.4210/25.11.4210/graphene202x",
    "nhcw800f": "leaba/25.11.4210/25.11.4210/graphene202x",
    "nh4010f": "brcm/13.3.0.0_odp/13.3.0.0_odp/tomahawk5",
    "nh4215f": "brcm/14.2.0.0_odp/14.2.0.0_odp/tomahawk6",
    "nh4220f": "brcm/14.2.0.0_odp/14.2.0.0_odp/tomahawk6",
}

# --enable-production-features key per model (SaiAgentTestRunner).
PROD_FEATURES_KEY: dict[str, str] = {
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


def sai_skip_known_bad(model: str) -> str:
    key = SAI_KNOWN_BAD_KEY.get(model)
    return f" --skip-known-bad-tests {key}" if key else ""


def benchmark_skip_known_bad(model: str) -> str:
    # sai_bench.materialized_JSON keys on vendor/sdk/asic (3-part), unlike the SAI
    # known-bad files which use vendor/coldboot-sai/warmboot-sai/asic. Collapse the
    # duplicated SDK segment so the benchmark platform key matches the config;
    # otherwise the lookup misses and unsupported (VOQ/Fabric/SRv6) benchmarks run.
    key = SAI_KNOWN_BAD_KEY.get(model)
    if not key:
        return ""
    parts = key.split("/")
    if len(parts) == 4 and parts[1] == parts[2]:
        key = f"{parts[0]}/{parts[1]}/{parts[3]}"
    return f" --skip-known-bad-tests {key}"


def fboss2_skip_known_bad(model: str) -> str:
    sai_key = SAI_KNOWN_BAD_KEY.get(model)
    if not sai_key:
        return ""
    vendor, sdk = sai_key.split("/")[:2]
    platform = SAI_AGENT_CONFIG_NAME.get(model, model)
    return f" --skip-known-bad-tests {platform}/{vendor}-{sdk}"


# asicToFeatureNames in asic_production_features.materialized_JSON says a chip
# supports a feature with no SDK-version awareness - sai_agent_test_runner.py's
# _filter_tests only ever checks against that flat list.
# featureSupportSpecs[].supportedFrom[].minSdkVersion is upstream metadata
# that needs to be taken into account. The helpers below cross-reference the
# two, using the SDK version each model is actually pinned to (the same one
# SAI_KNOWN_BAD_KEY already declares), so SaiAgentTestRunner can upload a
# filtered copy of the JSON before --enable-production-features runs.

def sdk_version_for_model(model: str) -> str | None:
    """This model's pinned SDK version, e.g. "14.2.0.0_odp" or "25.11.4210".

    None for models missing from that table. Compared on (major, minor)
    only (see sdk_version_meets_minimum) -- verified to order correctly
    for both BRCM's "X.Y.0.0_odp" scheme and Leaba's "YY.M.build" scheme.
    """
    key = SAI_KNOWN_BAD_KEY.get(model)
    if not key:
        return None
    parts = key.split("/")
    if len(parts) != 4:
        return None
    return parts[1]


def parse_sdk_version(version: str) -> tuple[int, int] | None:
    match = re.match(r"^(\d+)\.(\d+)", version)
    if not match:
        return None
    return (int(match.group(1)), int(match.group(2)))


def sdk_version_meets_minimum(current: str, minimum: str) -> bool:
    """Compare sdk version on (major, minor) only
    """
    current_parsed = parse_sdk_version(current)
    minimum_parsed = parse_sdk_version(minimum)
    if current_parsed is None or minimum_parsed is None:
        return True
    return current_parsed >= minimum_parsed


def sdk_excluded_feature_names(
    data: dict, asic: str, current_sdk_version: str
) -> set[str]:
    """Feature names in asicToFeatureNames[asic] whose featureSupportSpecs
    minSdkVersion exceeds current_sdk_version.
    """
    id_to_name = dict(
        zip(
            data.get("asicToFeatures", {}).get(asic, []),
            data.get("asicToFeatureNames", {}).get(asic, []),
            strict=False,
        )
    )
    excluded_names = set()
    for spec in data.get("featureSupportSpecs", []):
        name = id_to_name.get(spec.get("feature"))
        if name is None:
            continue
        for support in spec.get("supportedFrom", []):
            if asic not in support.get("asics", []):
                continue
            min_version = support.get("minSdkVersion")
            if min_version and not sdk_version_meets_minimum(
                current_sdk_version, min_version
            ):
                excluded_names.add(name)
    return excluded_names


def sdk_gate_production_features(
    data: dict, asic: str, excluded_names: set[str]
) -> dict:
    """Return a copy of the production-features JSON with asicToFeatureNames[asic]
    stripped of excluded_names. Other asics are left untouched.
    """
    filtered = copy.deepcopy(data)
    names = filtered.get("asicToFeatureNames", {})
    if asic in names:
        names[asic] = [n for n in names[asic] if n not in excluded_names]
    return filtered
