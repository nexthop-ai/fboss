"""Cabling-aware test execution shared by the QSFP and link runners: parse the
DUT's ports-info/snake-pairs data, split filters into copper-safe /
media-strict / optics-only passes, and run each pass against the right ports.
"""

import json
import logging
import os
from collections.abc import Mapping
from pathlib import Path

from tests.libs.test_runner.base import normalize_model
from tests.libs.test_runner.platform_configs import LINK_QSFP_TEST_CONFIG_NAME
from tests.libs.test_runner.platform_mapping import load_platform_mapping, repo_dir
from tests.libs.test_runner.variants import (
    cage_of,
    CageInfo,
    HostApp,
    MAX_VARIANT,
    Variant,
    VariantError,
    VariantNotApplicable,
    VariantResolution,
    derive_variant_chain,
    is_well_formed,
    load_full_platform_mapping,
    parse_variant,
    resolve_pairs,
)

logger = logging.getLogger("test_runner")


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


# Per-gtest --test-run-timeout passed to run_test.py; the floor matches its
# default. Tests that walk every transceiver twice (verifyResetControl) measure
# ~10s per port, so 15s/port leaves 50% margin.
_DEFAULT_TEST_RUN_TIMEOUT_SECS = 1200
_TEST_RUN_TIMEOUT_PER_PORT_SECS = 15


def _scaled_test_run_timeout(n_ports: int) -> int:
    return max(_DEFAULT_TEST_RUN_TIMEOUT_SECS, _TEST_RUN_TIMEOUT_PER_PORT_SECS * n_ports)


def neighbor_pairs(ports: list[str], pairs: dict[str, str]) -> list[tuple[str, str]]:
    """Resolve real neighbors for this pass's ports, once per cable.

    Matched by cage, not port name: `pairs` only ever names lane 1, while
    `ports` may include other lanes of the same cage. A cage with no usable
    peer contributes nothing (caller keeps its self-pair); a matched cage
    contributes only its first port, so a same-cage self-pair can't clobber it.
    """
    ports_by_cage: dict[str, list[str]] = {}
    for port in ports:
        ports_by_cage.setdefault(cage_of(port), []).append(port)

    peer_cage = {}
    for port, peer in pairs.items():
        a, z = cage_of(port), cage_of(peer)
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


class CablingAwareRunnerMixin:
    """Copper-safe vs optics-only filter split, shared by QsfpTestRunner and
    LinkTestRunner. Subclasses set _OPTICS_ONLY_FILTER_SUBSTRINGS and may
    override _prepare_pass() if the DUT config needs to change per pass.
    """

    _OPTICS_ONLY_FILTER_SUBSTRINGS: tuple[str, ...] = ()
    # Test cases verifying per-port media compliance; run only against
    # _strict_eligible_ports().
    _MEDIA_STRICT_FILTER_SUBSTRINGS: tuple[str, ...] = ()
    _PORTS_INFO_ENV_VAR = "TEST_PORTS_INFO"
    _SNAKE_PAIRS_ENV_VAR = "TEST_SNAKE_PAIRS"

    _VARIANT_SUMMARY_PREFIX = "TEST"

    def __init__(self):
        super().__init__()
        self._cached_base_config = None
        self._cached_port_map = None
        self._cached_full_mapping = None
        self._media_by_port: dict[str, str | None] = {}
        self._media_tech_by_port: dict[str, str | None] = {}
        self._transmitter_tech_by_port: dict[str, str | None] = {}
        self._is_copper_by_port: dict[str, bool | None] = {}
        self._host_speeds_by_port: dict[str, list[int] | None] = {}
        self._host_apps_by_port: dict[str, list[HostApp] | None] = {}
        # Set by _run_cabling_aware per pass; None on the max path.
        self._pass_variant_resolution: VariantResolution | None = None

    @classmethod
    def _config_name(cls, model: str) -> str:
        return LINK_QSFP_TEST_CONFIG_NAME.get(model, model)

    def _variant_name(self) -> str:
        return (self.tc or {}).get("variant") or "max"

    def _is_variant_run(self) -> bool:
        """Answered without the platform mapping: the no-cabling-data guards
        run before a model is guaranteed."""
        return self._variant_name().lower() != "max"

    def _report_variant_skip(self, reason: str, skip_tr_xml: bool) -> bool:
        """Report a variant this DUT cannot run as an all-skipped result.

        A run that leaves no tr.xml is recorded as FILE_ERR by the executor,
        and these wrappers are scheduled fleet-wide, so a platform lacking a
        variant has to look skipped rather than broken.
        """
        logger.info("%s", reason)
        if not skip_tr_xml:
            self._merge_junit_results([], skipped=[(self._variant_name(), reason)])
            self.normalize_test_results_file()
        return True

    def _requested_variant(self, config_name: str) -> Variant:
        """The requested variant from test_context["variant"]; absent means max.

        A well-formed variant this platform's mapping cannot program raises
        VariantNotApplicable (wrappers are scheduled fleet-wide); a malformed
        string stays a hard error.
        """
        if not self._is_variant_run():
            # The max path must not depend on the platform mapping: a model
            # whose mapping is missing still has to run at max.
            return MAX_VARIANT
        value = self._variant_name()
        cages = self._full_platform_mapping(config_name)
        if not cages:
            raise RuntimeError(f"platform mapping for {config_name} yielded no cages")
        try:
            variant = parse_variant(value, derive_variant_chain(cages))
        except VariantError as e:
            if is_well_formed(value):
                raise VariantNotApplicable(f"variant {value} is not supported on this platform: {e}") from e
            raise
        return variant

    def _full_platform_mapping(self, config_name: str) -> dict[str, CageInfo]:
        if self._cached_full_mapping is None:
            self._cached_full_mapping = load_full_platform_mapping(config_name)
        return self._cached_full_mapping

    # Cap on the lane rate a passive DAC may be asked to run in a breakout
    # variant. None means unconstrained: the qsfp tests program the module and
    # do not need the link, so only the link runner sets this.
    _VARIANT_PASSIVE_CU_MAX_LANE_SPEED_MBPS: int | None = None

    # Logical ports per datapath by config name. Only the link runner creates
    # agent ports, so only it can overflow one; the others leave this empty.
    _VARIANT_LOGICAL_PORTS_PER_DATAPATH: Mapping[str, int] = {}

    def _resolve_variant_pairs(
        self, pairs: dict[str, str], variant: Variant, config_name: str
    ) -> VariantResolution:
        """Resolve snake pairs for a non-max variant; requires _load_cabling to
        have populated the per-port module data first."""
        resolution = resolve_pairs(
            pairs,
            variant,
            self._full_platform_mapping(config_name),
            self._host_speeds_by_port,
            self._is_copper_by_port,
            self._host_apps_by_port,
            media_tech=self._media_tech_by_port,
            max_passive_cu_lane_speed=self._VARIANT_PASSIVE_CU_MAX_LANE_SPEED_MBPS,
            logical_ports_per_datapath=self._VARIANT_LOGICAL_PORTS_PER_DATAPATH.get(config_name),
        )
        logger.info(resolution.summary(self._VARIANT_SUMMARY_PREFIX))
        return resolution

    def _load_snake_pairs(self) -> dict[str, str]:
        return _load_json_pairs(os.getenv(self._SNAKE_PAIRS_ENV_VAR))

    def _pass_pairs(self, ports: list[str]) -> dict[str, str]:
        """Snake pairs with both ends inside this pass's port set."""
        allowed = set(ports)
        return {
            port: peer
            for port, peer in self._load_snake_pairs().items()
            if port in allowed and peer in allowed
        }

    def _load_base_config_and_port_map(self, base_config_dir: Path, config_name: str) -> tuple[dict, dict]:
        """Load and cache the base config JSON + platform-mapping port map.

        _prepare_pass() is called once per pass (main/optics), and both inputs
        are the same across passes for a given run, so cache them on first
        load instead of re-reading + re-parsing per pass.
        """
        if self._cached_base_config is None:
            base_path = repo_dir(base_config_dir) / f"{config_name}.materialized_JSON"
            try:
                with open(base_path, encoding="utf-8") as f:
                    self._cached_base_config = json.load(f)
            except (OSError, ValueError) as e:
                raise RuntimeError(f"Failed to load base config {base_path}: {e}") from e
            self._cached_port_map = load_platform_mapping(config_name)
        return self._cached_base_config, self._cached_port_map

    def _prepare_pass(self, model: str, ports: list[str]) -> None:  # noqa: ARG002
        pass

    def _load_cabling(self, cabling_path: str) -> tuple[list[str], list[str], dict[str, str | None]]:
        """Parse TEST_PORTS_INFO: {port: {"media_technology", "transmitter_technology",
        "media_interface"}}.

        Returns (all_ports, optics_ports, media_by_port). Optics eligibility
        (module with firmware/DSP) derives from media_technology; the
        port-profile medium from transmitter_technology (COPPER covers DAC and
        AEC), falling back to media_technology when a module reports UNKNOWN
        (e.g. loopback plugs).
        """
        try:
            with open(cabling_path, encoding="utf-8") as f:
                cabling = json.load(f)
        except (OSError, ValueError) as e:
            raise RuntimeError(f"Failed to load ports-info file {cabling_path}: {e}") from e
        all_ports = list(cabling)
        optics_ports = [
            p
            for p, info in cabling.items()
            if info.get("media_technology") not in (None, "PASSIVE_CU")
        ]
        media_by_port = {p: info.get("media_interface") for p, info in cabling.items()}
        self._media_by_port = media_by_port
        self._media_tech_by_port = {p: info.get("media_technology") for p, info in cabling.items()}
        self._transmitter_tech_by_port = {
            p: info.get("transmitter_technology") for p, info in cabling.items()
        }
        self._is_copper_by_port = {
            p: (
                tech == "COPPER"
                if (tech := self._transmitter_tech_by_port[p]) in ("COPPER", "OPTICAL", "BACKPLANE")
                else (info["media_technology"] == "PASSIVE_CU" if info.get("media_technology") else None)
            )
            for p, info in cabling.items()
        }
        self._host_speeds_by_port = {p: info.get("host_speeds") for p, info in cabling.items()}
        # [[speed_mbps, host_lanes], ...]; absent from files written before nhtools emitted it.
        self._host_apps_by_port = {
            p: [(speed, lanes) for speed, lanes in apps] if (apps := info.get("host_apps")) else None
            for p, info in cabling.items()
        }
        return all_ports, optics_ports, media_by_port

    def _gate_filters(
        self, patterns: list[str], media_by_port: dict[str, str | None], optics_ports: list[str]
    ) -> tuple[list[str], list[tuple[str, str]]]:
        """Hook for cabling-aware filter gating. Base impl is a no-op (keeps
        all patterns); LinkTestRunner overrides to drop patterns the DUT's
        cabling can't satisfy."""
        return list(patterns), []

    def _strict_eligible_ports(self, model: str, ports: list[str]) -> list[str]:  # noqa: ARG002
        """Hook: ports the media-strict pass may verify. Base impl keeps all."""
        return list(ports)

    @classmethod
    def _split_filters(cls, filters: list[str]) -> tuple[list[str], list[str], list[str]]:
        """Bucket filters by substring match against optics-only and
        media-strict test names."""
        copper_safe, strict, optics_only = [], [], []
        for f in filters:
            if any(s in f for s in cls._OPTICS_ONLY_FILTER_SUBSTRINGS):
                optics_only.append(f)
            elif any(s in f for s in cls._MEDIA_STRICT_FILTER_SUBSTRINGS):
                strict.append(f)
            else:
                copper_safe.append(f)
        return copper_safe, strict, optics_only

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
    def _bucket_expressions(cls, patterns: list[str], suffix: str) -> tuple[str, str, str]:
        """Bucket patterns, then rejoin each side into a --gtest_filter expression."""
        buckets = cls._split_filters(patterns)
        return tuple(":".join(b) + suffix if b else "" for b in buckets)

    @classmethod
    def _split_gtest_filter(cls, expr: str) -> tuple[str, str, str]:
        """Split a single --gtest_filter expression into
        copper-safe/media-strict/optics-only sub-expressions, sharing the
        negative-pattern suffix.

        Colon-separated positives are classified the same way _split_filters
        buckets tc["filters"], so a mixed TESTFILTER runs as separate passes
        against the right port set each, instead of once against the wrong one.
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
            # Refuse to silently run the max config under a variant test name.
            if self._is_variant_run():
                return self._report_variant_skip(
                    "variant runs require TEST_PORTS_INFO cabling data", skip_tr_xml
                )
            return super()._run_test_impl(test_context, skip_tr_xml)
        return self._run_cabling_aware(cabling_path, test_context, skip_tr_xml)

    def _run_cabling_aware(self, cabling_path, test_context, skip_tr_xml):
        # setup()/deploy already ran in the base run_test() before this call.
        model = normalize_model(self.tc["model"])
        config_name = self._config_name(model)
        all_ports, optics_ports, media_by_port = self._load_cabling(cabling_path)
        # Both gates run before any DUT mutation, so reporting a skip here
        # cannot discard results: nothing has executed yet.
        try:
            variant = self._requested_variant(config_name)
            if not variant.is_max:
                pairs = self._load_snake_pairs()
                if not pairs:
                    raise VariantNotApplicable(
                        "variant runs require TEST_SNAKE_PAIRS cabling data"
                    )
                # Zero supported pairs is missing coverage, not a failure.
                resolution = self._resolve_variant_pairs(pairs, variant, config_name)
                if resolution.supported == 0:
                    raise VariantNotApplicable(resolution.summary(self._VARIANT_SUMMARY_PREFIX))
        except VariantNotApplicable as e:
            return self._report_variant_skip(str(e), skip_tr_xml)
        # Breakout multiplies the port count, so scale the timeout with it.
        self._test_run_timeout_secs = _scaled_test_run_timeout(len(all_ports) * variant.factor)
        logger.info(
            "test-run-timeout %ds for %d cabled ports", self._test_run_timeout_secs, len(all_ports)
        )

        gtest_filter = self.tc.get("gtest_filter")
        if gtest_filter:
            patterns, suffix = self._parse_gtest_filter(gtest_filter)
        else:
            patterns, suffix = list(self.tc["filters"]), ""

        kept_patterns, skipped = self._gate_filters(patterns, media_by_port, optics_ports)
        if gtest_filter:
            copper_bucket, strict_bucket, optics_bucket = self._bucket_expressions(kept_patterns, suffix)
        else:
            copper_bucket, strict_bucket, optics_bucket = self._split_filters(kept_patterns)

        passes = []  # list of (label, filter_value, ports)
        if copper_bucket:
            passes.append(("main", copper_bucket, all_ports))
        if strict_bucket:
            strict_ports = self._strict_eligible_ports(model, all_ports)
            if strict_ports:
                passes.append(("strict", strict_bucket, strict_ports))
            else:
                logger.info(
                    "No ports with a verifiable media profile on this DUT; "
                    "skipping media-strict tests: %s",
                    strict_bucket,
                )
                skipped.extend(
                    (pattern, "no ports with a verifiable media profile on this DUT")
                    for pattern in ([strict_bucket] if gtest_filter else strict_bucket)
                )
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
            for pass_index, (label, filter_value, ports) in enumerate(passes):
                # Decide per-pass variant viability here (not by raising out
                # of pre_test) so earlier pass results survive.
                self._pass_variant_resolution = None
                if not variant.is_max:
                    resolution = self._resolve_variant_pairs(
                        self._pass_pairs(ports), variant, config_name
                    )
                    if not resolution.expanded_pairs:
                        reason = f"no pair supports variant {variant.name} among this pass's ports"
                        logger.info("Skipping %s pass: %s", label, reason)
                        skipped.extend(
                            (pattern, reason)
                            for pattern in ([filter_value] if gtest_filter else filter_value)
                        )
                        continue
                    self._pass_variant_resolution = resolution
                if gtest_filter:
                    self.tc["gtest_filter"] = filter_value
                else:
                    self.tc["filters"] = filter_value
                # The previous pass's run_test.py restarted the agents on exit.
                self._wait_for_agent_settled()
                self._prepare_pass(model, ports)
                self.pre_test()  # fresh warm/cold-boot state wipe per pass
                pre_test_called = True
                log_local, xml_local = self._pass_local_paths(label)
                success = self._execute_test_binary(model, log_local, xml_local, skip_tr_xml)
                pass_results.append(success)
                ran_labels.append(label)
                if not success:
                    logger.error("%s %s pass failed; aborting remaining passes", type(self).__name__, label)
                    for _, remaining, _ in passes[pass_index + 1:]:
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
