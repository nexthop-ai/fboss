"""Route-scale agent_hw tests, split into their own suite and run at INFO FBOSS
logging so their logs stay under the T-Recs ingest size limit."""

test_context = {
    "filters": [
        "*RouteScale*",
        # Exclusion Criteria
        "-*Alpm*",
    ],
}


def test_route_scale_agent_hw_tests(sai_agent_test_runner):
    assert sai_agent_test_runner.run_test(test_context, fboss_logging="fboss=INFO")
