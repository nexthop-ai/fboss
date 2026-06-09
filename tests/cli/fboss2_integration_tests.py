# fboss2 CLI integration tests.
#
# Runs the fboss2_integration_test gtest binary (bundled in
# forwarding-stack-tests.tar) against a running FBOSS instance via
# run_test.py's fboss2_integration subcommand. The runner detects/starts
# the production agents, cold-boots per test, and restores on teardown;
# run_test.py also filters known-bad cases from the bundled
# fboss2_integration_known_bad_tests file, so the filter below selects the
# full suite.
test_context = {
    "filters": [
        "*",
    ],
}


def test_fboss2_integration_tests(fboss2_integration_test_runner):
    assert fboss2_integration_test_runner.run_test(test_context)
