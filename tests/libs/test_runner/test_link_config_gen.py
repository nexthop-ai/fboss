"""Unit tests for LinkTestRunner._overlay_cabling config generation.

The generated link test config is fully re-synthesized from the platform
mapping and netbox cabling: cabled ports enabled, every other cage's
controlling port disabled, per-port vlan/vlanPort/interface with synthesized
IPs. The base config contributes only non-port scaffolding, so its
front-panel content (including inconsistencies) must never leak through.
"""

import copy

import pytest

from tests.libs.test_runner.runner import LinkTestRunner, _PortInfo


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
PAIRS = {"eth1/1/1": "eth1/2/1", "eth1/2/1": "eth1/1/1"}
PORT_MAP = {
    "eth1/1/1": _PortInfo(logical_id=301, profile_id=39, speed=400000),
    "eth1/2/1": _PortInfo(logical_id=302, profile_id=39, speed=400000),
    "eth1/3/1": _PortInfo(logical_id=303, profile_id=39, speed=800000),
    "eth1/3/5": _PortInfo(logical_id=304, profile_id=38, speed=400000),
    "eth1/4/1": _PortInfo(logical_id=305, profile_id=39, speed=800000),
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
        pm["rcy1/1/1"] = _PortInfo(logical_id=400, profile_id=39, speed=800000)
        pm["fab1/5/1"] = _PortInfo(logical_id=401, profile_id=39, speed=800000)
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
        big_map = {
            f"eth1/{cage}/1": _PortInfo(logical_id=cage, profile_id=39, speed=800000)
            for cage in range(1, 300)
        }
        with pytest.raises(ValueError, match="ran out of vlans"):
            LinkTestRunner._overlay_cabling(_base_config(["eth1/9/1"]), PAIRS, big_map)
