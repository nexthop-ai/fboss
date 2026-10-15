"""SaiAgentTestRunner: minSdkVersion gating of --production-features, end to
end through _upload_sdk_gated_production_features with scp mocked. The pure
version comparisons live in platform_configs.py (see test_platform_configs.py).
"""

from tests.libs.test_runner import SaiAgentTestRunner, SaiTestRunner

from .helpers import json_scp, make_runner, production_features_fixture


def _runner_with_mocked_scp(dut_json):
    """Returns (runner, uploads): uploads fills in as put_file is called."""
    runner = make_runner(SaiAgentTestRunner)
    return runner, json_scp(runner, dut_json)


def test_sai_runner_test_args_carry_config_and_known_bad():
    args = SaiTestRunner().test_args("nh4215f")
    assert args.startswith("sai --config ./share/hw_test_configs/")
    assert "--skip-known-bad-tests brcm/" in args


def test_enable_production_features_uploads_filtered_file_when_gating_applies():
    runner, uploaded = _runner_with_mocked_scp(production_features_fixture())
    result = runner._enable_production_features("nh4215f")  # tomahawk6 @ 14.2.0.0_odp

    assert " --enable-production-features tomahawk6" in result
    assert (
        f" --production-features {runner._REMOTE_SDK_GATED_PRODUCTION_FEATURES_PATH}"
        in result
    )
    runner.scp_client.get_file.assert_called_once()
    runner.scp_client.put_file.assert_called_once()
    names = uploaded[runner._REMOTE_SDK_GATED_PRODUCTION_FEATURES_PATH]["asicToFeatureNames"]
    assert names["tomahawk6"] == ["L3_FORWARDING"]
    assert names["tomahawk5"] == [
        "L3_FORWARDING",
        "SRV6_MIDPOINT",
    ]


def test_upload_sdk_gated_production_features_skips_upload_when_nothing_excluded():
    # SDK new enough that neither SRV6 feature needs excluding.
    runner, _ = _runner_with_mocked_scp(production_features_fixture())

    path = runner._upload_sdk_gated_production_features("tomahawk6", "15.4.0.0_odp")

    assert path is None
    runner.scp_client.get_file.assert_called_once()  # still reads, to find out
    runner.scp_client.put_file.assert_not_called()


def test_enable_production_features_no_override_when_nothing_excluded():
    # minSdkVersion of "1.0_odp" is below every real SAI_KNOWN_BAD_KEY pin,
    # so nh4215f's real 14.2.0.0_odp already satisfies it -- nothing to gate.
    fixture = production_features_fixture()
    for spec in fixture["featureSupportSpecs"]:
        for support in spec["supportedFrom"]:
            support["minSdkVersion"] = "1.0_odp"
    runner, _ = _runner_with_mocked_scp(fixture)

    result = runner._enable_production_features("nh4215f")

    assert result == " --enable-production-features tomahawk6"
    assert "--production-features" not in result
    runner.scp_client.get_file.assert_called_once()  # still checks
    runner.scp_client.put_file.assert_not_called()


def test_enable_production_features_leaba_no_exclusions():
    # The brcm-shaped fixture has no g202x entries, so there's nothing to
    # exclude -- but the vendor is still checked: get_file is called.
    runner, _ = _runner_with_mocked_scp(production_features_fixture())

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
    runner, uploaded = _runner_with_mocked_scp(fixture)
    result = runner._enable_production_features("wedge800cact")  # g202x @ 25.11.4210

    assert " --enable-production-features g202x" in result
    assert (
        f" --production-features {runner._REMOTE_SDK_GATED_PRODUCTION_FEATURES_PATH}"
        in result
    )
    names = uploaded[runner._REMOTE_SDK_GATED_PRODUCTION_FEATURES_PATH]["asicToFeatureNames"]
    assert names["g202x"] == ["L3_FORWARDING"]


def test_enable_production_features_unmapped_model_returns_empty():
    runner, _ = _runner_with_mocked_scp(production_features_fixture())

    assert runner._enable_production_features("no-such-model") == ""
    runner.scp_client.get_file.assert_not_called()


def test_enable_production_features_not_connected_falls_back_silently():
    runner = SaiAgentTestRunner()  # ssh_client/scp_client still None

    result = runner._enable_production_features("nh4215f")

    assert result == " --enable-production-features tomahawk6"


def test_upload_sdk_gated_production_features_get_file_failure_fails_open():
    runner, _ = _runner_with_mocked_scp(production_features_fixture())
    runner.scp_client.get_file.side_effect = None
    runner.scp_client.get_file.return_value = (1, "no such file")

    path = runner._upload_sdk_gated_production_features("tomahawk6", "14.2.0.0_odp")

    assert path is None
    runner.scp_client.put_file.assert_not_called()


def test_upload_sdk_gated_production_features_bad_json_fails_open():
    runner, _ = _runner_with_mocked_scp(production_features_fixture())

    def fake_get_file_bad_json(remote_path, local_path):  # noqa: ARG001
        with open(local_path, "w", encoding="utf-8") as f:
            f.write("{not valid json")
        return (0, "")

    runner.scp_client.get_file.side_effect = fake_get_file_bad_json

    path = runner._upload_sdk_gated_production_features("tomahawk6", "14.2.0.0_odp")

    assert path is None
    runner.scp_client.put_file.assert_not_called()


def test_enable_production_features_caches_upload_across_calls():
    runner, _ = _runner_with_mocked_scp(production_features_fixture())

    first = runner._enable_production_features("nh4215f")
    second = runner._enable_production_features("nh4215f")

    assert first == second
    runner.scp_client.get_file.assert_called_once()
    runner.scp_client.put_file.assert_called_once()


def test_enable_production_features_cache_is_keyed_by_asic_and_sdk_version():
    runner, _ = _runner_with_mocked_scp(production_features_fixture())

    runner._enable_production_features("nh4215f")  # tomahawk6 @ 14.2.0.0_odp
    runner._enable_production_features("minipack3")  # tomahawk5 @ 13.3.0.0_odp

    assert runner.scp_client.get_file.call_count == 2
    assert runner.scp_client.put_file.call_count == 2
