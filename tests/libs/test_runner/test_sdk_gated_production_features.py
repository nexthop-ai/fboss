"""Unit tests for SaiAgentTestRunner's minSdkVersion gating.

asicToFeatureNames in asic_production_features.materialized_JSON says a chip
architecturally supports a feature, with no SDK-version awareness --
--enable-production-features's subset-check in sai_agent_test_runner.py
consults that flat list only. featureSupportSpecs[].supportedFrom[].
minSdkVersion is upstream metadata nothing in the OSS test-selection
pipeline reads. These tests cover the pure comparison/filtering helpers in
platform_configs.py, plus the end-to-end _upload_sdk_gated_production_features /
_enable_production_features flow with scp_client mocked.
"""

import json
from unittest.mock import MagicMock

import pytest

from tests.libs.test_runner import SaiAgentTestRunner
from tests.libs.test_runner.platform_configs import (
    parse_sdk_version,
    sdk_excluded_feature_names,
    sdk_gate_production_features,
    sdk_version_for_model,
    sdk_version_meets_minimum,
)

# ---------------------------------------------------------------------------
# sdk_version_for_model
# ---------------------------------------------------------------------------


def test_sdk_version_for_model_brcm():
    assert sdk_version_for_model("nh4215f") == "14.2.0.0_odp"
    assert sdk_version_for_model("nh4220f") == "14.2.0.0_odp"
    assert sdk_version_for_model("minipack3") == "13.3.0.0_odp"


def test_sdk_version_for_model_leaba():
    assert sdk_version_for_model("wedge800cact") == "25.11.4210"
    assert sdk_version_for_model("nhcw800f") == "25.11.4210"


def test_sdk_version_for_model_missing_returns_none():
    # wedge800bnhp is a known gap: present in SaiAgentTestRunner's model->asic
    # table but absent from SAI_KNOWN_BAD_KEY, so gating silently stays off
    # for it.
    assert sdk_version_for_model("wedge800bnhp") is None
    assert sdk_version_for_model("no-such-model") is None


# ---------------------------------------------------------------------------
# parse_sdk_version / sdk_version_meets_minimum
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "version,expected",
    [
        ("14.2.0.0_odp", (14, 2)),
        ("15.4_ea_odp", (15, 4)),
        ("12.0.0.0_dnx_odp", (12, 0)),
        ("25.11.4210", (25, 11)),
        ("garbage", None),
        ("", None),
    ],
)
def test_parse_sdk_version(version, expected):
    assert parse_sdk_version(version) == expected


@pytest.mark.parametrize(
    "current,minimum,expected",
    [
        ("14.2.0.0_odp", "15.4_ea_odp", False),
        ("15.4.0.0_odp", "15.4_ea_odp", True),
        ("15.5.0.0_odp", "15.4_ea_odp", True),
        ("14.2.0.0_odp", "14.2.0.0_odp", True),
        ("14.2.0.0_odp", "12.0.0.0_dnx_odp", True),
        # Numeric, not lexicographic, comparison of the minor component --
        # also the real wedge800cact/nhcw800f SRv6 case (minSdkVersion
        # 26.2.4210, pinned at 25.11.4210 -- correctly excluded).
        ("25.11.4210", "26.2.4210", False),
        ("25.5.4210", "25.11.4210", False),
        # minSdkVersion is a single scalar -- "supported from here on" is
        # all it can mean, so this correctly reads as "supported" at
        # 25.11.4210. It doesn't need to represent feature 112's later
        # regression (Leaba link debounce, g202x): the schema has no way
        # to encode that, so upstream necessarily excludes it via a
        # separate list instead (sai_graphene202x_25_11_unsupported_tests
        # -- see sdk_version_for_model's docstring), not via
        # minSdkVersion.
        ("25.11.4210", "25.5.4210", True),
    ],
)
def test_sdk_version_meets_minimum(current, minimum, expected):
    assert sdk_version_meets_minimum(current, minimum) is expected


def test_sdk_version_meets_minimum_fails_open_on_unparsable():
    assert sdk_version_meets_minimum("garbage", "15.4_ea_odp") is True
    assert sdk_version_meets_minimum("14.2.0.0_odp", "garbage") is True


# ---------------------------------------------------------------------------
# sdk_excluded_feature_names / sdk_gate_production_features
# ---------------------------------------------------------------------------


def _production_features_fixture():
    """Minimal asic_production_features.materialized_JSON shape, modeled on
    the real SRv6 entries (feature 100 = SRV6_ENCAP, 104 = SRV6_MIDPOINT).
    """
    return {
        "asicToFeatures": {"tomahawk6": [1, 100, 104], "tomahawk5": [1, 104]},
        "asicToFeatureNames": {
            "tomahawk6": ["L3_FORWARDING", "SRV6_ENCAP", "SRV6_MIDPOINT"],
            "tomahawk5": ["L3_FORWARDING", "SRV6_MIDPOINT"],
        },
        "featureSupportSpecs": [
            {
                "feature": 100,
                "supportedFrom": [
                    {
                        "asics": ["tomahawk5", "tomahawk6"],
                        "sdk": 1,
                        "minSdkVersion": "15.4_ea_odp",
                    }
                ],
            },
            {
                "feature": 104,
                "supportedFrom": [
                    {
                        "asics": ["tomahawk5", "tomahawk6"],
                        "sdk": 1,
                        "minSdkVersion": "15.4_ea_odp",
                    }
                ],
            },
        ],
    }


def test_sdk_excluded_feature_names_below_minimum():
    data = _production_features_fixture()
    assert sdk_excluded_feature_names(data, "tomahawk6", "14.2.0.0_odp") == {
        "SRV6_ENCAP",
        "SRV6_MIDPOINT",
    }


def test_sdk_excluded_feature_names_meets_minimum():
    data = _production_features_fixture()
    assert sdk_excluded_feature_names(data, "tomahawk6", "15.4.0.0_odp") == set()


def test_sdk_excluded_feature_names_scoped_to_requested_asic():
    data = _production_features_fixture()
    # tomahawk5 only carries SRV6_MIDPOINT (feature 104) -- SRV6_ENCAP (100)
    # isn't in its asicToFeatures list at all, so it can't be excluded from it.
    assert sdk_excluded_feature_names(data, "tomahawk5", "14.2.0.0_odp") == {
        "SRV6_MIDPOINT"
    }


def test_sdk_excluded_feature_names_unknown_asic_returns_empty():
    data = _production_features_fixture()
    assert sdk_excluded_feature_names(data, "unknown_asic", "1.0.0.0_odp") == set()


def test_sdk_gate_production_features_only_touches_requested_asic():
    data = _production_features_fixture()
    excluded = {"SRV6_ENCAP", "SRV6_MIDPOINT"}

    filtered = sdk_gate_production_features(data, "tomahawk6", excluded)

    assert filtered["asicToFeatureNames"]["tomahawk6"] == ["L3_FORWARDING"]
    assert (
        filtered["asicToFeatureNames"]["tomahawk5"]
        == data["asicToFeatureNames"]["tomahawk5"]
    )
    assert filtered["asicToFeatures"] == data["asicToFeatures"]
    assert filtered["featureSupportSpecs"] == data["featureSupportSpecs"]
    # Original is never mutated -- callers hold a live reference to it.
    assert data["asicToFeatureNames"]["tomahawk6"] == [
        "L3_FORWARDING",
        "SRV6_ENCAP",
        "SRV6_MIDPOINT",
    ]


def test_sdk_gate_production_features_no_exclusions_is_a_no_op_copy():
    data = _production_features_fixture()
    filtered = sdk_gate_production_features(data, "tomahawk6", set())
    assert filtered == data
    assert filtered is not data


# ---------------------------------------------------------------------------
# SaiAgentTestRunner._upload_sdk_gated_production_features /
# _enable_production_features -- end-to-end with scp_client mocked
# ---------------------------------------------------------------------------


def _runner_with_mocked_scp(dut_json):
    """A SaiAgentTestRunner with ssh_client/scp_client mocked as if setup()
    had already connected. scp_client.get_file writes dut_json to whatever
    local path it's given, matching real scp semantics closely enough for
    the code under test (which only reads/writes that local file).
    """
    runner = SaiAgentTestRunner()
    runner.ssh_client = MagicMock()
    runner.scp_client = MagicMock()

    def fake_get_file(remote_path, local_path):  # noqa: ARG001
        with open(local_path, "w", encoding="utf-8") as f:
            json.dump(dut_json, f)
        return (0, "")

    runner.scp_client.get_file.side_effect = fake_get_file
    runner.scp_client.put_file.return_value = (0, "ok")
    return runner


def test_enable_production_features_uploads_filtered_file_when_gating_applies():
    runner = _runner_with_mocked_scp(_production_features_fixture())
    uploaded = {}

    def fake_put_file(local_path, remote_path):  # noqa: ARG001
        # Captured synchronously, before the runner's own `finally:
        # os.unlink(local_path)` deletes this temp file.
        with open(local_path, encoding="utf-8") as f:
            uploaded["content"] = json.load(f)
        return (0, "ok")

    runner.scp_client.put_file.side_effect = fake_put_file

    result = runner._enable_production_features("nh4215f")  # tomahawk6 @ 14.2.0.0_odp

    assert " --enable-production-features tomahawk6" in result
    assert (
        f" --production-features {runner._REMOTE_SDK_GATED_PRODUCTION_FEATURES_PATH}"
        in result
    )
    runner.scp_client.get_file.assert_called_once()
    runner.scp_client.put_file.assert_called_once()
    assert uploaded["content"]["asicToFeatureNames"]["tomahawk6"] == ["L3_FORWARDING"]
    assert uploaded["content"]["asicToFeatureNames"]["tomahawk5"] == [
        "L3_FORWARDING",
        "SRV6_MIDPOINT",
    ]


def test_upload_sdk_gated_production_features_skips_upload_when_nothing_excluded():
    # SDK new enough that neither SRV6 feature needs excluding.
    runner = _runner_with_mocked_scp(_production_features_fixture())

    path = runner._upload_sdk_gated_production_features("tomahawk6", "15.4.0.0_odp")

    assert path is None
    runner.scp_client.get_file.assert_called_once()  # still reads, to find out
    runner.scp_client.put_file.assert_not_called()


def test_enable_production_features_no_override_when_nothing_excluded():
    # minSdkVersion of "1.0_odp" is below every real SAI_KNOWN_BAD_KEY pin,
    # so nh4215f's real 14.2.0.0_odp already satisfies it -- nothing to gate.
    fixture = _production_features_fixture()
    for spec in fixture["featureSupportSpecs"]:
        for support in spec["supportedFrom"]:
            support["minSdkVersion"] = "1.0_odp"
    runner = _runner_with_mocked_scp(fixture)

    result = runner._enable_production_features("nh4215f")

    assert result == " --enable-production-features tomahawk6"
    assert "--production-features" not in result
    runner.scp_client.get_file.assert_called_once()  # still checks
    runner.scp_client.put_file.assert_not_called()


def test_enable_production_features_leaba_no_exclusions():
    # The brcm-shaped fixture has no g202x entries, so there's nothing to
    # exclude -- but the vendor is still checked: get_file is called.
    runner = _runner_with_mocked_scp(_production_features_fixture())

    result = runner._enable_production_features("wedge800cact")

    assert result == " --enable-production-features g202x"
    assert "--production-features" not in result
    runner.scp_client.get_file.assert_called_once()
    runner.scp_client.put_file.assert_not_called()


def test_enable_production_features_gates_leaba_srv6():
    # Same shape as the real wedge800cact/nhcw800f SRv6 entry -- see
    # sdk_version_for_model's docstring for why (major, minor) comparison
    # holds for Leaba's calendar-style versioning.
    fixture = {
        "asicToFeatures": {"g202x": [1, 100]},
        "asicToFeatureNames": {"g202x": ["L3_FORWARDING", "SRV6_ENCAP"]},
        "featureSupportSpecs": [
            {
                "feature": 100,
                "supportedFrom": [
                    {"asics": ["yuba", "g202x"], "sdk": 2, "minSdkVersion": "26.2.4210"}
                ],
            }
        ],
    }
    runner = _runner_with_mocked_scp(fixture)
    uploaded = {}

    def fake_put_file(local_path, remote_path):  # noqa: ARG001
        with open(local_path, encoding="utf-8") as f:
            uploaded["content"] = json.load(f)
        return (0, "ok")

    runner.scp_client.put_file.side_effect = fake_put_file

    result = runner._enable_production_features("wedge800cact")  # g202x @ 25.11.4210

    assert " --enable-production-features g202x" in result
    assert (
        f" --production-features {runner._REMOTE_SDK_GATED_PRODUCTION_FEATURES_PATH}"
        in result
    )
    assert uploaded["content"]["asicToFeatureNames"]["g202x"] == ["L3_FORWARDING"]


def test_enable_production_features_unmapped_model_returns_empty():
    runner = _runner_with_mocked_scp(_production_features_fixture())

    assert runner._enable_production_features("no-such-model") == ""
    runner.scp_client.get_file.assert_not_called()


def test_enable_production_features_not_connected_falls_back_silently():
    runner = SaiAgentTestRunner()  # ssh_client/scp_client still None

    result = runner._enable_production_features("nh4215f")

    assert result == " --enable-production-features tomahawk6"


def test_upload_sdk_gated_production_features_get_file_failure_fails_open():
    runner = _runner_with_mocked_scp(_production_features_fixture())
    runner.scp_client.get_file.side_effect = None
    runner.scp_client.get_file.return_value = (1, "no such file")

    path = runner._upload_sdk_gated_production_features("tomahawk6", "14.2.0.0_odp")

    assert path is None
    runner.scp_client.put_file.assert_not_called()


def test_upload_sdk_gated_production_features_bad_json_fails_open():
    runner = _runner_with_mocked_scp(_production_features_fixture())

    def fake_get_file_bad_json(remote_path, local_path):  # noqa: ARG001
        with open(local_path, "w", encoding="utf-8") as f:
            f.write("{not valid json")
        return (0, "")

    runner.scp_client.get_file.side_effect = fake_get_file_bad_json

    path = runner._upload_sdk_gated_production_features("tomahawk6", "14.2.0.0_odp")

    assert path is None
    runner.scp_client.put_file.assert_not_called()


def test_enable_production_features_caches_upload_across_calls():
    runner = _runner_with_mocked_scp(_production_features_fixture())

    first = runner._enable_production_features("nh4215f")
    second = runner._enable_production_features("nh4215f")

    assert first == second
    runner.scp_client.get_file.assert_called_once()
    runner.scp_client.put_file.assert_called_once()


def test_enable_production_features_cache_is_keyed_by_asic_and_sdk_version():
    runner = _runner_with_mocked_scp(_production_features_fixture())

    runner._enable_production_features("nh4215f")  # tomahawk6 @ 14.2.0.0_odp
    runner._enable_production_features("minipack3")  # tomahawk5 @ 13.3.0.0_odp

    assert runner.scp_client.get_file.call_count == 2
    assert runner.scp_client.put_file.call_count == 2
