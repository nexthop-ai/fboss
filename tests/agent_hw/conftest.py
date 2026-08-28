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

from prepare.fanout_ports import get_dut_facing_fanout_ports
from prepare.mint.fanout import FanoutManager

logger = logging.getLogger(__name__)


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
        shut = get_dut_facing_fanout_ports(testbed)
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
