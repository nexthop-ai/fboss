"""LinkTestRunner: the link test config it synthesizes from the platform
mapping and cabling, the qsfp_service config it stages on the DUT, and the
filter gates (media, PTP flap) it applies on a cabling-aware run."""

import copy

import pytest

from tests.libs.test_runner import LinkTestRunner

from .helpers import (
    VARIANT_FLAGFILE,
    drive_cabling_aware,
    json_scp,
    make_cabling_runner,
    make_port,
    make_runner,
    symmetric_pairs,
)


def _base_config(port_names, mgmt=True, default_vlan=4094):
    sw = {
        "defaultVlan": default_vlan,
        "ports": [],
        "vlans": [{"id": default_vlan, "intfID": default_vlan, "name": f"vlan{default_vlan}"}],
        "vlanPorts": [],
        "interfaces": [],
    }
    for i, name in enumerate(port_names):
        vlan = 2000 + i
        sw["ports"].append(
            {
                "logicalID": 100 + i,
                "name": name,
                "state": 2,
                "speed": 400000,
                "profileID": 38,
                "ingressVlan": vlan,
                "portType": 0,
                "expectedLLDPValues": {},
            }
        )
        sw["vlans"].append({"id": vlan, "intfID": vlan, "name": f"vlan{vlan}"})
        sw["vlanPorts"].append({"vlanID": vlan, "logicalPort": 100 + i})
        sw["interfaces"].append(
            {
                "intfID": vlan,
                "vlanID": vlan,
                "ipAddresses": [f"24{i:02d}::/64", f"{10 + i}.0.0.0/24"],
            }
        )
    if mgmt:
        sw["ports"].append(
            {
                "logicalID": 999,
                "name": "eth1/33/1",
                "state": 2,
                "speed": 10000,
                "profileID": 1,
                "ingressVlan": default_vlan,
                "portType": 4,
                "expectedLLDPValues": {},
            }
        )
    return {"sw": sw}


# Two cabled cages (1, 2) and two uncabled cages (3, 4) with breakout subports.
PAIRS = symmetric_pairs(("eth1/1/1", "eth1/2/1"))
PORT_MAP = {
    "eth1/1/1": make_port(301),
    "eth1/2/1": make_port(302),
    "eth1/3/1": make_port(303),
    "eth1/3/5": make_port(304, 38),
    "eth1/4/1": make_port(305),
}


def _assert_consistent(config):
    sw = config["sw"]
    vlan_ids = {v["id"] for v in sw["vlans"]} | {sw["defaultVlan"]}
    for port in sw["ports"]:
        assert port["ingressVlan"] in vlan_ids, port
    for vp in sw["vlanPorts"]:
        assert vp["vlanID"] in vlan_ids, vp
    for intf in sw["interfaces"]:
        assert intf["vlanID"] in vlan_ids, intf
    names = [p["name"] for p in sw["ports"]]
    assert len(names) == len(set(names))


class TestOverlayCabling:
    """The generated link test config is fully re-synthesized from the platform
    mapping and netbox cabling: cabled ports enabled, every other cage's
    controlling port disabled, per-port vlan/vlanPort/interface with synthesized
    IPs. The base config contributes only non-port scaffolding, so its
    front-panel content (including inconsistencies) must never leak through."""

    def test_ports_fully_synthesized(self):
        base = _base_config(["eth1/1/1", "eth1/9/1"])
        out = LinkTestRunner._overlay_cabling(base, PAIRS, PORT_MAP)
        _assert_consistent(out)
        ports = {p["name"]: p for p in out["sw"]["ports"] if p["portType"] == 0}
        # Cabled ports enabled; one disabled filler per uncabled cage's
        # controlling port; base front-panel ports (eth1/9/1) gone.
        assert set(ports) == {"eth1/1/1", "eth1/2/1", "eth1/3/1", "eth1/4/1"}
        assert all(ports[n]["state"] == 2 for n in PAIRS)
        assert ports["eth1/3/1"]["state"] == 1
        assert ports["eth1/4/1"]["state"] == 1
        assert ports["eth1/3/1"]["speed"] == 800000
        mgmt = [p for p in out["sw"]["ports"] if p["portType"] == 4]
        assert len(mgmt) == 1 and mgmt[0]["name"] == "eth1/33/1"

    def test_no_base_front_panel_content_survives(self):
        base = _base_config(["eth1/9/1", "eth1/10/1"])
        base_ips = {tuple(i["ipAddresses"]) for i in base["sw"]["interfaces"]}
        base_logical_ports = {100, 101}
        out = LinkTestRunner._overlay_cabling(base, PAIRS, PORT_MAP)
        sw = out["sw"]
        assert not any(p["name"] in {"eth1/9/1", "eth1/10/1"} for p in sw["ports"])
        assert not any(tuple(i["ipAddresses"]) in base_ips for i in sw["interfaces"])
        assert not any(vp["logicalPort"] in base_logical_ports for vp in sw["vlanPorts"])

    def test_inconsistent_base_config_is_immaterial(self):
        # A base port/vlanPort/interface referencing an undefined vlan (the
        # NOS-14349 hole) must not reach the generated config.
        base = _base_config(["eth1/9/1"])
        base["sw"]["ports"].append(
            {
                "logicalID": 320,
                "name": "eth1/12/8",
                "state": 2,
                "speed": 100000,
                "profileID": 56,
                "ingressVlan": 2047,
                "portType": 0,
                "expectedLLDPValues": {},
            }
        )
        base["sw"]["vlanPorts"].append({"vlanID": 2047, "logicalPort": 320})
        base["sw"]["interfaces"].append({"intfID": 2047, "vlanID": 2047, "ipAddresses": []})
        out = LinkTestRunner._overlay_cabling(base, PAIRS, PORT_MAP)
        _assert_consistent(out)
        sw = out["sw"]
        assert not any(i["vlanID"] == 2047 for i in sw["interfaces"])
        assert not any(vp["vlanID"] == 2047 for vp in sw["vlanPorts"])

    def test_synthesized_interfaces_have_unique_ips(self):
        base = _base_config(["eth1/9/1"])
        out = LinkTestRunner._overlay_cabling(base, PAIRS, PORT_MAP)
        sw = out["sw"]
        fp_vlans = {p["ingressVlan"] for p in sw["ports"] if p["portType"] == 0}
        ips = [tuple(i["ipAddresses"]) for i in sw["interfaces"] if i["vlanID"] in fp_vlans]
        assert len(ips) == 4
        assert all(len(addrs) == 2 for addrs in ips)
        assert len(set(ips)) == len(ips)

    def test_generation_is_deterministic(self):
        base = _base_config(["eth1/9/1"])
        out1 = LinkTestRunner._overlay_cabling(copy.deepcopy(base), PAIRS, PORT_MAP)
        out2 = LinkTestRunner._overlay_cabling(base, PAIRS, PORT_MAP)
        assert out1 == out2

    def test_fillers_carry_no_template_lldp_expectations(self):
        base = _base_config(["eth1/9/1"])
        base["sw"]["ports"][0]["expectedLLDPValues"] = {"2": "eth1/4/1"}
        out = LinkTestRunner._overlay_cabling(base, PAIRS, PORT_MAP)
        fillers = [p for p in out["sw"]["ports"] if p.get("portType") == 0 and p["state"] == 1]
        assert fillers and all(p["expectedLLDPValues"] == {} for p in fillers)

    def test_vlanless_interfaces_are_kept(self):
        base = _base_config(["eth1/9/1"])
        base["sw"]["interfaces"].append({"intfID": 9000, "ipAddresses": ["9::1/64"]})
        out = LinkTestRunner._overlay_cabling(base, PAIRS, PORT_MAP)
        assert any(i.get("intfID") == 9000 for i in out["sw"]["interfaces"])

    def test_non_eth_mapping_ports_get_no_filler(self):
        base = _base_config(["eth1/9/1"])
        pm = dict(PORT_MAP)
        pm["rcy1/1/1"] = make_port(400)
        pm["fab1/5/1"] = make_port(401)
        out = LinkTestRunner._overlay_cabling(base, PAIRS, pm)
        names = {p["name"] for p in out["sw"]["ports"]}
        assert "rcy1/1/1" not in names and "fab1/5/1" not in names

    def test_no_pairs_raises(self):
        with pytest.raises(ValueError, match="no cabling pairs"):
            LinkTestRunner._overlay_cabling(_base_config(["eth1/1/1"]), {}, PORT_MAP)

    def test_unmapped_port_raises(self):
        with pytest.raises(ValueError, match="not in the platform mapping"):
            LinkTestRunner._overlay_cabling(_base_config(["eth1/1/1"]), PAIRS, {})

    def test_vlan_band_overflow_raises(self):
        big_map = {f"eth1/{cage}/1": make_port(cage) for cage in range(1, 2200)}
        with pytest.raises(ValueError, match="ran out of vlans"):
            LinkTestRunner._overlay_cabling(_base_config(["eth1/9/1"]), PAIRS, big_map)

    def test_full_breakout_on_high_port_count_platform_fits_vlan_band(self):
        # 128 cages (m4062nhp, the fleet's widest) at an 8-way breakout is 1024
        # synthesized ports, well past the 513 any shipping platform reaches.
        port_map = {
            f"eth1/{cage}/{sub}": make_port(cage * 10 + sub, 23)
            for cage in range(1, 129)
            for sub in range(1, 9)
        }
        pairs = symmetric_pairs(
            *((f"eth1/{a}/{sub}", f"eth1/{a + 1}/{sub}") for a in range(1, 129, 2) for sub in range(1, 9))
        )
        # mgmt=False: the fixture's mgmt port name would collide with cage 33.
        base = _base_config(["eth1/9/1"], mgmt=False)
        out1 = LinkTestRunner._overlay_cabling(copy.deepcopy(base), pairs, port_map)
        out2 = LinkTestRunner._overlay_cabling(base, pairs, port_map)
        assert out1 == out2
        _assert_consistent(out1)
        enabled = [p for p in out1["sw"]["ports"] if p["portType"] == 0 and p["state"] == 2]
        assert len(enabled) == 1024
        assert out1["sw"]["switchSettings"]["ecmpWidth"] == 1024
        assert out1["defaultCommandLineArgs"]["ecmp_width"] == "1024"

    @staticmethod
    def _wide_pairs(cages):
        port_map = {f"eth1/{cage}/1": make_port(cage) for cage in range(1, cages + 1)}
        pairs = symmetric_pairs(*((f"eth1/{a}/1", f"eth1/{a + 1}/1") for a in range(1, cages, 2)))
        return port_map, pairs

    def test_ecmp_width_untouched_at_default_or_below(self):
        out = LinkTestRunner._overlay_cabling(_base_config(["eth1/9/1"]), PAIRS, PORT_MAP)
        assert "switchSettings" not in out["sw"]
        assert "defaultCommandLineArgs" not in out
        port_map, pairs = self._wide_pairs(64)
        out = LinkTestRunner._overlay_cabling(_base_config(["eth1/9/1"], mgmt=False), pairs, port_map)
        assert "switchSettings" not in out["sw"]

    def test_ecmp_width_follows_cabled_ports_in_flag_and_config(self):
        port_map, pairs = self._wide_pairs(66)
        base = _base_config(["eth1/9/1"], mgmt=False)
        base["defaultCommandLineArgs"] = {"ecmp_width": "64", "other": "x"}
        out = LinkTestRunner._overlay_cabling(base, pairs, port_map)
        assert out["sw"]["switchSettings"]["ecmpWidth"] == 66
        assert out["defaultCommandLineArgs"] == {"ecmp_width": "66", "other": "x"}

    def test_ecmp_width_is_never_lowered(self):
        port_map, pairs = self._wide_pairs(66)
        base = _base_config(["eth1/9/1"], mgmt=False)
        base["defaultCommandLineArgs"] = {"ecmp_width": "320"}
        out = LinkTestRunner._overlay_cabling(copy.deepcopy(base), pairs, port_map)
        assert "switchSettings" not in out["sw"]
        assert out["defaultCommandLineArgs"] == {"ecmp_width": "320"}
        base["sw"]["switchSettings"] = {"ecmpWidth": 512, "l2LearningMode": 0}
        out = LinkTestRunner._overlay_cabling(base, pairs, port_map)
        assert out["sw"]["switchSettings"] == {"ecmpWidth": 512, "l2LearningMode": 0}

    def test_profile_overrides_set_speed_and_profile(self):
        port_map = {
            **PORT_MAP,
            "eth1/1/1": make_port(301, 39, 25),
            "eth1/1/3": make_port(311, 25),
            "eth1/2/1": make_port(302, 39, 25),
            "eth1/2/3": make_port(312, 25),
        }
        pairs = symmetric_pairs(("eth1/1/1", "eth1/2/1"), ("eth1/1/3", "eth1/2/3"))
        overrides = {name: 25 for name in pairs}
        out = LinkTestRunner._overlay_cabling(
            _base_config(["eth1/9/1"]), pairs, port_map, profile_overrides=overrides
        )
        _assert_consistent(out)
        ports = {p["name"]: p for p in out["sw"]["ports"] if p["portType"] == 0}
        for name, peer in pairs.items():
            assert ports[name]["profileID"] == 25
            assert ports[name]["speed"] == 200000
            assert ports[name]["expectedLLDPValues"] == {"2": peer}
        # Uncabled-cage fillers keep their default max profile.
        assert ports["eth1/3/1"]["profileID"] == 39
        assert ports["eth1/3/1"]["state"] == 1

    def test_profile_override_unsupported_raises(self):
        with pytest.raises(ValueError, match="does not support profile"):
            LinkTestRunner._overlay_cabling(
                _base_config(["eth1/9/1"]), PAIRS, PORT_MAP, profile_overrides={"eth1/1/1": 23}
            )

    def test_max_output_unchanged_by_override_plumbing(self):
        base = _base_config(["eth1/9/1"])
        out_default = LinkTestRunner._overlay_cabling(copy.deepcopy(base), PAIRS, PORT_MAP)
        out_none = LinkTestRunner._overlay_cabling(base, PAIRS, PORT_MAP, profile_overrides=None)
        assert out_default == out_none


def _stage(system_config, flagfile=None):
    """Run _stage_qsfp_config against a fake DUT; return the uploaded config."""
    runner = make_runner(LinkTestRunner, flagfile=flagfile)
    uploaded = json_scp(runner, system_config)
    runner._stage_qsfp_config()
    assert runner.scp_client.get_file.call_args[0][0] == LinkTestRunner._SYSTEM_QSFP_CONFIG_PATH
    return uploaded[LinkTestRunner._REMOTE_QSFP_CONFIG_PATH]


class TestStageQsfpConfig:
    """The qsfp_service config staged on the DUT for the link tests."""

    def test_disables_fsdb_subscription_and_remediation(self):
        staged = _stage({"defaultCommandLineArgs": {"mode": "wedge800cact"}})
        assert staged["defaultCommandLineArgs"] == {
            "mode": "wedge800cact",
            "subscribe_to_state_from_fsdb": "false",
            "remediation_enabled": "false",
        }

    def test_overrides_system_values(self):
        staged = _stage(
            {
                "defaultCommandLineArgs": {
                    "subscribe_to_state_from_fsdb": "true",
                    "remediation_enabled": "true",
                }
            }
        )
        assert staged["defaultCommandLineArgs"]["subscribe_to_state_from_fsdb"] == "false"
        assert staged["defaultCommandLineArgs"]["remediation_enabled"] == "false"

    def test_creates_args_when_system_config_has_none(self):
        staged = _stage({"transceiverConfigOverrides": []})
        assert staged["transceiverConfigOverrides"] == []
        assert staged["defaultCommandLineArgs"] == {
            "subscribe_to_state_from_fsdb": "false",
            "remediation_enabled": "false",
        }

    def test_keeps_variant_flags(self):
        staged = _stage({}, flagfile=VARIANT_FLAGFILE)
        assert staged["defaultCommandLineArgs"]["hwrev_state1_substate1_respin0"] == "true"
        assert staged["defaultCommandLineArgs"]["remediation_enabled"] == "false"


_CABLED_PAIR = symmetric_pairs(("eth1/25/1", "eth1/26/1"))
_TRAFFIC = "*LinkTest*trafficRxTx*"

# Class names the two media-templated PRBS variants generate; the gate requires the
# media on both ends of a pair for the first and only one end for the second.
_TCVR_L = "*Prbs_TCVR_L*{}*"
_ASIC_TCVR_S = "*Prbs_ASIC*TCVR_S*{}*"

_NO_MEDIA_TOKEN = "PRBS filter names no media interface"


def _gate(monkeypatch, patterns, media_by_port, *, optics_ports=None, pairs=None, variant=None):
    """_gate_filters on a runner with no DUT behind it. media_by_port is what
    _load_cabling reports (None for a port without a media code); every port
    counts as optical unless optics_ports says otherwise."""
    runner = LinkTestRunner()
    runner.tc = {"model": "m4062nhp", "variant": variant}
    # Sort ports by name rather than by a platform mapping this test does not ship.
    runner._cached_port_map = {}
    monkeypatch.setattr(runner, "_load_snake_pairs", lambda: pairs or {})
    return runner._gate_filters(
        patterns, media_by_port, list(media_by_port) if optics_ports is None else optics_ports
    )


class TestMediaGate:
    """A PRBS filter pattern is dropped when its media is not cabled on this
    DUT, so the gtest binary never aborts on an empty port set."""

    def test_uncabled_media_is_skipped_and_cabled_runs(self, monkeypatch):
        kept, skipped = _gate(
            monkeypatch,
            [_TCVR_L.format("FR4_400G"), _TCVR_L.format("FR8_800G")],
            {"eth1/25/1": "FR8_800G", "eth1/26/1": "FR8_800G"},
            pairs=_CABLED_PAIR,
        )
        assert kept == [_TCVR_L.format("FR8_800G")]
        assert skipped == [(_TCVR_L.format("FR4_400G"), "no FR4_400G optics cabled on this DUT")]

    def test_media_on_one_end_only_skips_tcvr_l_but_keeps_asic(self, monkeypatch):
        kept, skipped = _gate(
            monkeypatch,
            [_TCVR_L.format("FR4_400G"), _ASIC_TCVR_S.format("FR4_400G")],
            {"eth1/25/1": "FR4_400G", "eth1/26/1": "DR4_400G"},
            pairs=_CABLED_PAIR,
        )
        assert kept == [_ASIC_TCVR_S.format("FR4_400G")]
        assert skipped == [(_TCVR_L.format("FR4_400G"), "no FR4_400G optics cabled on this DUT")]

    def test_breakout_media_code_is_per_port(self, monkeypatch):
        # A 2x400G FR4 part reports FR4_400G per port; FR4_2x400G is no PRBS class.
        kept, skipped = _gate(
            monkeypatch,
            [_TCVR_L.format("FR4_400G"), _TCVR_L.format("FR4_2x400G")],
            {"eth1/25/1": "FR4_400G", "eth1/26/1": "FR4_400G"},
            pairs=_CABLED_PAIR,
        )
        assert kept == [_TCVR_L.format("FR4_400G")]
        assert skipped == [(_TCVR_L.format("FR4_2x400G"), _NO_MEDIA_TOKEN)]

    def test_missing_media_code_skips_as_unavailable(self, monkeypatch):
        kept, skipped = _gate(
            monkeypatch,
            [_TCVR_L.format("FR4_400G"), _TRAFFIC],
            {"eth1/25/1": None, "eth1/26/1": None},
            pairs=_CABLED_PAIR,
        )
        assert kept == [_TRAFFIC]
        assert skipped == [(_TCVR_L.format("FR4_400G"), "port media interface unavailable")]

    def test_no_snake_pairs_falls_back_to_cabled_anywhere(self, monkeypatch):
        kept, skipped = _gate(
            monkeypatch,
            [_TCVR_L.format("FR4_400G"), _TCVR_L.format("FR8_800G")],
            {"eth1/25/1": "FR4_400G", "eth1/26/1": "DR4_400G"},
        )
        assert kept == [_TCVR_L.format("FR4_400G")]
        assert skipped == [(_TCVR_L.format("FR8_800G"), "no FR8_800G optics cabled on this DUT")]

    @pytest.mark.parametrize("optics_ports", [None, []], ids=["optical", "all_copper"])
    def test_prbs_pattern_without_media_token_is_skipped(self, monkeypatch, optics_ports):
        # A bare *Prbs* expands to every media-templated class, including empty ones.
        kept, skipped = _gate(
            monkeypatch,
            ["*Prbs*", _TRAFFIC],
            {"eth1/25/1": "CR8_800G", "eth1/26/1": "CR8_800G"},
            optics_ports=optics_ports,
            pairs=_CABLED_PAIR,
        )
        assert kept == [_TRAFFIC]
        assert skipped == [("*Prbs*", _NO_MEDIA_TOKEN)]

    def test_variant_run_skips_every_prbs_pattern(self, monkeypatch):
        # At a breakout speed qsfp_service reports the running application's
        # media code, so the full-speed-templated classes find no port.
        prbs = [_TCVR_L.format("FR8_800G"), _ASIC_TCVR_S.format("FR8_800G")]
        kept, skipped = _gate(
            monkeypatch, [*prbs, _TRAFFIC], {"eth1/25/1": "FR8_800G", "eth1/26/1": "FR8_800G"}, variant="2x400G"
        )
        assert kept == [_TRAFFIC]
        reason = "PRBS classes match full-speed media codes only; not run on breakout variants"
        assert skipped == [(p, reason) for p in prbs]

    def test_max_run_keeps_cabled_prbs_pattern(self, monkeypatch):
        pattern = _TCVR_L.format("FR8_800G")
        kept, skipped = _gate(monkeypatch, [pattern], {"eth1/25/1": "FR8_800G", "eth1/26/1": "FR8_800G"}, variant="max")
        assert kept == [pattern]
        assert skipped == []


def _optical(media):
    return {"media_technology": "OPTICAL_SMF", "media_interface": media}


def _run_media_gated(tmp_path, monkeypatch, filters, ports_info, pairs=None):
    """Drive LinkTestRunner._run_cabling_aware() in filters-list mode with
    TEST_PORTS_INFO/TEST_SNAKE_PAIRS backing the gate."""
    runner, cabling_path = make_cabling_runner(
        LinkTestRunner, tmp_path, ports_info, filters=filters, pairs=pairs, monkeypatch=monkeypatch
    )
    runner._cached_port_map = {}
    return drive_cabling_aware(runner, cabling_path)


class TestMediaGatePassComposition:
    """CR media needs an optical/active port: the PRBS pair source drops
    passive copper, so a CR pattern belongs to the optics pass."""

    def test_cr8_on_active_module_runs_in_optics_pass(self, tmp_path, monkeypatch):
        run = _run_media_gated(
            tmp_path, monkeypatch,
            filters=[_TCVR_L.format("CR8_800G")],
            ports_info={"eth1/25/1": _optical("CR8_800G"), "eth1/26/1": _optical("CR8_800G")},
            pairs=_CABLED_PAIR,
        )
        assert run.result is True
        assert run.execute_calls == [[_TCVR_L.format("CR8_800G")]]
        assert run.skipped == []
        assert run.prepare_calls == [("m4062nhp", ["eth1/25/1", "eth1/26/1"])]

    def test_cr8_on_passive_dac_is_skipped(self, tmp_path, monkeypatch):
        copper = {"media_technology": "PASSIVE_CU", "media_interface": "CR8_800G"}
        run = _run_media_gated(
            tmp_path, monkeypatch,
            filters=[_TCVR_L.format("CR8_800G")],
            ports_info={"eth1/25/1": copper, "eth1/26/1": copper},
            pairs=_CABLED_PAIR,
        )
        assert run.result is True
        assert run.execute_calls == []
        assert run.skipped == [
            (_TCVR_L.format("CR8_800G"), "no optical/active transceivers cabled on this DUT")
        ]


def _copper_ports(port_range):
    return {f"eth1/{n}/1": None for n in port_range}


def _snake(*pairs):
    return symmetric_pairs(*((f"eth1/{a}/1", f"eth1/{z}/1") for a, z in pairs))


_PTP_FLAP = "*PtpTests*enablePtpPortDown*"
_PTP_NO_SURVIVOR_REASON = (
    "no snake pair outside the first 5 flapped ports; PTP loop unroutable after flap"
)


class TestPtpFlapGate:
    """The PTP flap tests take the first 5 cabled ports down for good, so the
    pattern is skipped unless a snake pair sits fully outside that set."""

    def _gate_ptp(self, monkeypatch, patterns, ports, pairs):
        return _gate(monkeypatch, patterns, _copper_ports(ports), optics_ports=[], pairs=pairs)

    def test_surviving_pair_runs(self, monkeypatch):
        kept, skipped = self._gate_ptp(
            monkeypatch, [_PTP_FLAP], range(1, 11), _snake((1, 2), (3, 4), (5, 6), (7, 8), (9, 10))
        )
        assert kept == [_PTP_FLAP]
        assert skipped == []

    @pytest.mark.parametrize("pattern", [_PTP_FLAP, "*PtpTests*verifyPtpTcAfterLinkFlap*"])
    def test_all_pairs_touched_by_flap_skips(self, monkeypatch, pattern):
        kept, skipped = self._gate_ptp(
            monkeypatch, [pattern, _TRAFFIC], range(1, 7), _snake((1, 2), (3, 4), (5, 6))
        )
        assert kept == [_TRAFFIC]
        assert skipped == [(pattern, _PTP_NO_SURVIVOR_REASON)]

    def test_no_snake_pairs_data_does_not_gate(self, monkeypatch):
        kept, skipped = self._gate_ptp(monkeypatch, [_PTP_FLAP], range(1, 7), None)
        assert kept == [_PTP_FLAP]
        assert skipped == []

    def test_pair_ends_must_both_be_cabled(self, monkeypatch):
        # Pair (7, 8) would survive the flap, but eth1/8/1 is not cabled.
        kept, skipped = self._gate_ptp(
            monkeypatch, [_PTP_FLAP], range(1, 8), _snake((1, 2), (3, 4), (5, 6), (7, 8))
        )
        assert kept == []
        assert skipped == [(_PTP_FLAP, _PTP_NO_SURVIVOR_REASON)]

    def test_unpaired_ports_do_not_shift_the_flapped_set(self, monkeypatch):
        kept, skipped = self._gate_ptp(
            monkeypatch, [_PTP_FLAP], range(1, 11), _snake((5, 6), (7, 8), (9, 10))
        )
        assert kept == []
        assert skipped == [(_PTP_FLAP, _PTP_NO_SURVIVOR_REASON)]
