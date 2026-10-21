import pytest

pytestmark = pytest.mark.topology("fboss-standalone")

test_context = {
    "filters": [
        "*FlowletSwitching*",
        "*FlowletSourcePortPrune*",
        "*FlowletArsSourcePortPrune*",
        "*FlowletArsDlbFailPackets*",
        "*AdjFrr*",
        # Exclusion Criteria
        "-*Ecmp*",
    ],
}

def test_flowlet_frr_agent_hw_tests(sai_agent_test_runner):
    assert sai_agent_test_runner.run_test(test_context)
