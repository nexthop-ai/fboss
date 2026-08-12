"""Admin-shut fanout ports facing the DUT while agent_hw tests run.

agent_hw tests expect ports to stay oper-down after LinkStateToggler removes
their loopback mode, but ports cabled to a fanout retrain against the
fanout's TX and bounce back up. Shutting the fanout side removes
the peer signal; the tests themselves only ever use MAC loopback, which sits
upstream of the cable. Changes are not saved to the fanout's startup config,
and testbed prepare re-enables admin-down fanout ports, so any missed
restore self-heals.
"""

import logging
import os
import pytest

from device.client.device_client import Device
from prepare.mint.fanout import FanoutManager
from prepare.sonic.base_testbed_setup import get_xcvr_to_ethernet_mapping
from testbed.testbed_client import TestbedClient

logger = logging.getLogger(__name__)


def _dut_facing_fanout_ports(testbed):
    """Map fanout name -> its Ethernet ports cabled to the testbed's DUT."""
    client = TestbedClient(testbed)
    dut_name = client.get_dut()[0].get_name()
    fanouts = {dev.get_name(): dev for dev in client.get_fanout()}
    mappings = {name: get_xcvr_to_ethernet_mapping(dev.get_model()) for name, dev in fanouts.items()}
    ports = {}
    for conn in Device(dut_name).get_all_connections():
        for sub in conn.sub_connections:
            for end, other in ((sub.conn_end_A, sub.conn_end_B), (sub.conn_end_B, sub.conn_end_A)):
                if (
                    other.device_name == dut_name
                    and end.device_name in fanouts
                    and end.device_port.name.startswith("XcvrSlot")
                ):
                    slot = int(end.device_port.name.removeprefix("XcvrSlot"))
                    ports.setdefault(end.device_name, set()).add(mappings[end.device_name][slot])
    return {name: sorted(p) for name, p in ports.items()}


def _set_admin_state(fanout_name, ports, up):
    logger.info("fanout %s ports %s -> admin %s", fanout_name, ports, "up" if up else "down")
    with FanoutManager(fanout_name) as fm:
        fm.switch.ethernet.create_interface_set(ports).mac.set_admin_state(up)


@pytest.fixture(scope="session", autouse=True)
def silence_fanout_ports():
    dut = os.getenv("DUT")
    if not dut or os.getenv("FBOSS_DEPLOY_ONLY") == "1":
        yield
        return

    testbed = dut.removesuffix("-dut")
    shut = {}
    try:
        shut = _dut_facing_fanout_ports(testbed)
    except Exception:
        logger.warning("could not resolve fanout ports for %s", testbed, exc_info=True)
    for fanout_name, ports in shut.items():
        try:
            _set_admin_state(fanout_name, ports, up=False)
        except Exception:
            logger.warning("could not silence %s ports %s", fanout_name, ports, exc_info=True)

    try:
        yield
    finally:
        for fanout_name, ports in shut.items():
            try:
                _set_admin_state(fanout_name, ports, up=True)
            except Exception:
                logger.warning("failed to restore %s ports %s", fanout_name, ports, exc_info=True)
