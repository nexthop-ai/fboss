"""platform_configs.py: the model to config/known-bad-key tables and the pure
SDK-version helpers behind SaiAgentTestRunner's production-feature gating."""

import pytest

from tests.libs.test_runner.platform_configs import (
    benchmark_skip_known_bad,
    fboss2_skip_known_bad,
    parse_sdk_version,
    sai_skip_known_bad,
    sdk_excluded_feature_names,
    sdk_gate_production_features,
    sdk_version_for_model,
    sdk_version_meets_minimum,
)

from .helpers import production_features_fixture


class TestKnownBadKeys:
    def test_sai_key_is_the_four_part_tuple(self):
        assert sai_skip_known_bad("nh4215f") == (
            " --skip-known-bad-tests brcm/14.2.0.0_odp/14.2.0.0_odp/tomahawk6"
        )

    @pytest.mark.parametrize(
        ("model", "expected"),
        [
            ("nh4215f", "brcm/14.2.0.0_odp/tomahawk6/m4062nhp"),
            ("minipack3", "brcm/13.3.0.0_odp/tomahawk5/montblanc"),
            ("nhcw800f", "leaba/25.11.4210/graphene202x/wedge800cact"),
        ],
    )
    def test_benchmark_key_is_asic_plus_platform(self, model, expected):
        """The SAI 4-tuple collapses to vendor/sdk/asic and gains the config codename,
        so a platform can carry its own sai_bench skips and still inherit the ASIC's."""
        assert benchmark_skip_known_bad(model) == f" --skip-known-bad-tests {expected}"

    def test_fboss2_key_is_platform_slash_vendor_sdk(self):
        assert fboss2_skip_known_bad("nh4215f") == " --skip-known-bad-tests m4062nhp/brcm-14.2.0.0_odp"
        assert fboss2_skip_known_bad("nhcw800f") == " --skip-known-bad-tests wedge800cact/leaba-25.11.4210"

    @pytest.mark.parametrize("fn", [sai_skip_known_bad, benchmark_skip_known_bad, fboss2_skip_known_bad])
    def test_unknown_model_adds_nothing(self, fn):
        assert fn("wedge800bnhp") == ""
        assert fn("no-such-model") == ""


class TestSdkVersionForModel:
    def test_brcm(self):
        assert sdk_version_for_model("nh4215f") == "14.2.0.0_odp"
        assert sdk_version_for_model("nh4220f") == "14.2.0.0_odp"
        assert sdk_version_for_model("minipack3") == "13.3.0.0_odp"

    def test_leaba(self):
        assert sdk_version_for_model("wedge800cact") == "25.11.4210"
        assert sdk_version_for_model("nhcw800f") == "25.11.4210"

    def test_missing_returns_none(self):
        # wedge800bnhp is a known gap: present in SaiAgentTestRunner's model->asic
        # table but absent from SAI_KNOWN_BAD_KEY, so gating silently stays off
        # for it.
        assert sdk_version_for_model("wedge800bnhp") is None
        assert sdk_version_for_model("no-such-model") is None


class TestSdkVersionComparison:
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
    def test_parse_sdk_version(self, version, expected):
        assert parse_sdk_version(version) == expected

    @pytest.mark.parametrize(
        "current,minimum,expected",
        [
            ("14.2.0.0_odp", "15.4_ea_odp", False),
            ("15.4.0.0_odp", "15.4_ea_odp", True),
            ("15.5.0.0_odp", "15.4_ea_odp", True),
            ("14.2.0.0_odp", "14.2.0.0_odp", True),
            ("14.2.0.0_odp", "12.0.0.0_dnx_odp", True),
            # Numeric, not lexicographic, minor comparison: the real
            # wedge800cact SRv6 case (minSdkVersion 26.2.4210 at 25.11.4210).
            ("25.11.4210", "26.2.4210", False),
            ("25.5.4210", "25.11.4210", False),
            ("25.11.4210", "25.5.4210", True),
        ],
    )
    def test_meets_minimum(self, current, minimum, expected):
        assert sdk_version_meets_minimum(current, minimum) is expected

    def test_meets_minimum_fails_open_on_unparsable(self):
        assert sdk_version_meets_minimum("garbage", "15.4_ea_odp") is True
        assert sdk_version_meets_minimum("14.2.0.0_odp", "garbage") is True


class TestSdkGating:
    def test_excluded_names_below_minimum(self):
        data = production_features_fixture()
        assert sdk_excluded_feature_names(data, "tomahawk6", "14.2.0.0_odp") == {
            "SRV6_ENCAP",
            "SRV6_MIDPOINT",
        }

    def test_excluded_names_meets_minimum(self):
        data = production_features_fixture()
        assert sdk_excluded_feature_names(data, "tomahawk6", "15.4.0.0_odp") == set()

    def test_excluded_names_scoped_to_requested_asic(self):
        data = production_features_fixture()
        # tomahawk5 only carries SRV6_MIDPOINT (feature 104) -- SRV6_ENCAP (100)
        # isn't in its asicToFeatures list at all, so it can't be excluded from it.
        assert sdk_excluded_feature_names(data, "tomahawk5", "14.2.0.0_odp") == {
            "SRV6_MIDPOINT"
        }

    def test_excluded_names_unknown_asic_returns_empty(self):
        data = production_features_fixture()
        assert sdk_excluded_feature_names(data, "unknown_asic", "1.0.0.0_odp") == set()

    def test_gate_only_touches_requested_asic(self):
        data = production_features_fixture()
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

    def test_gate_with_no_exclusions_is_a_copy(self):
        data = production_features_fixture()
        filtered = sdk_gate_production_features(data, "tomahawk6", set())
        assert filtered == data
        assert filtered is not data
