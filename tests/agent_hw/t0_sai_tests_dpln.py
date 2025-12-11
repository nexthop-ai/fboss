from tests.libs.hw_agent.lib_hw_agent_runner import hw_agent_test_runner as runner

test_context = {
    "filters" : [
        "*Empty*",
        "*Vlan*",
        "*NextHopGroup*",
        "*RouteNeighbor*"
        "*PortAdminState*",
    ],
}

def test_t0_sai_tests_dpln(runner):
    assert runner.run_test(test_context)
