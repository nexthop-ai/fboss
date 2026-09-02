"""SAI and SAI-agent hardware test runners."""

import json
import logging
import os
import tempfile

from tests.libs.test_runner.base import BaseHwTestRunner
from tests.libs.test_runner.deploy import (
    FBOSS_ROOT_ON_DUT,
    STACK_FORWARDING,
    STACK_SHARE,
)
from tests.libs.test_runner.platform_configs import (
    PROD_FEATURES_KEY,
    SAI_AGENT_CONFIG_NAME,
    sai_skip_known_bad,
    sdk_excluded_feature_names,
    sdk_gate_production_features,
    sdk_version_for_model,
)

logger = logging.getLogger("test_runner")


class SaiTestRunner(BaseHwTestRunner):
    """Runner for SAI hardware tests."""

    def test_args(self, model: str) -> str:
        config_name = SAI_AGENT_CONFIG_NAME.get(model, model)
        logger.info("model=%s hw_test_config=%s", model, config_name)
        return f"sai --config ./share/hw_test_configs/{config_name}.agent.materialized_JSON{sai_skip_known_bad(model)}"
    STACK = STACK_FORWARDING
    BINARIES = ("bin/sai_test-sai_impl",)
    REQUIRED_PATHS = (*BINARIES, *STACK_SHARE[STACK])


class SaiAgentTestRunner(BaseHwTestRunner):
    """Runner for SAI agent tests."""

    STACK = STACK_FORWARDING
    # Both binaries ship: --agent-run-mode picks mono vs multi at run time.
    BINARIES = ("bin/sai_agent_hw_test-sai_impl", "bin/multi_switch_agent_hw_test")
    REQUIRED_PATHS = (*BINARIES, *STACK_SHARE[STACK])

    _SYSTEM_PRODUCTION_FEATURES_PATH = (
        f"{FBOSS_ROOT_ON_DUT}/share/production_features/"
        "asic_production_features.materialized_JSON"
    )
    _REMOTE_SDK_GATED_PRODUCTION_FEATURES_PATH = (
        "/home/netops/sdk_gated_production_features.materialized_JSON"
    )

    def __init__(self):
        super().__init__()
        # Keyed by (asic, sdk_version); test_args() is called once per test
        # case in a batch, and each entry costs an ssh cat + scp put, so cache
        # across calls instead of re-uploading per test.
        self._sdk_gated_production_features_cache: dict[
            tuple[str, str], str | None
        ] = {}

    def _upload_sdk_gated_production_features(
        self, asic: str, current_sdk_version: str
    ) -> str | None:
        """Read the DUT's production-features JSON, drop any feature whose
        minSdkVersion exceeds current_sdk_version, and upload the filtered
        copy. Returns the remote path to pass as --production-features, or
        None -- run with the upstream default unchanged, either because
        nothing needs excluding at this SDK version or because something
        here failed.
        """
        if self.ssh_client is None or self.scp_client is None:
            return None
        with tempfile.NamedTemporaryFile(
            suffix=".materialized_JSON", delete=False
        ) as f:
            local_path = f.name
        try:
            exit_status, output = self.scp_client.get_file(
                self._SYSTEM_PRODUCTION_FEATURES_PATH, local_path
            )
            if exit_status != 0:
                logger.warning(
                    "Could not fetch %s from DUT (%s); running without "
                    "minSdkVersion gating",
                    self._SYSTEM_PRODUCTION_FEATURES_PATH,
                    output,
                )
                return None
            try:
                with open(local_path, encoding="utf-8") as f:
                    data = json.load(f)
            except json.JSONDecodeError:
                logger.warning(
                    "Production features JSON from DUT was unparseable; "
                    "running without minSdkVersion gating"
                )
                return None

            excluded_names = sdk_excluded_feature_names(
                data, asic, current_sdk_version
            )
            if not excluded_names:
                # Nothing to gate at this SDK version -- skip the upload and
                # let --enable-production-features read the DUT's default
                # file.
                return None

            filtered = sdk_gate_production_features(data, asic, excluded_names)
            with open(local_path, "w", encoding="utf-8") as f:
                json.dump(filtered, f, indent=4)

            exit_status, output = self.scp_client.put_file(
                local_path, self._REMOTE_SDK_GATED_PRODUCTION_FEATURES_PATH
            )
        finally:
            os.unlink(local_path)
        if exit_status != 0:
            logger.warning(
                "Failed to upload SDK-gated production features (%s); "
                "running without minSdkVersion gating",
                output,
            )
            return None
        return self._REMOTE_SDK_GATED_PRODUCTION_FEATURES_PATH

    def _enable_production_features(self, model: str) -> str:
        key = PROD_FEATURES_KEY.get(model)
        if not key:
            return ""
        sdk_version = sdk_version_for_model(model)
        features_path = None
        if sdk_version:
            cache_key = (key, sdk_version)
            if cache_key not in self._sdk_gated_production_features_cache:
                self._sdk_gated_production_features_cache[cache_key] = (
                    self._upload_sdk_gated_production_features(key, sdk_version)
                )
            features_path = self._sdk_gated_production_features_cache[cache_key]
        features_arg = f" --production-features {features_path}" if features_path else ""
        return f" --enable-production-features {key}{features_arg}"

    def test_args(self, model: str) -> str:
        config_name = SAI_AGENT_CONFIG_NAME.get(model, model)
        logger.info("model=%s hw_test_config=%s", model, config_name)
        return f"sai_agent --config ./share/hw_test_configs/{config_name}.agent.materialized_JSON \
            {sai_skip_known_bad(model)}{self._enable_production_features(model)}"
