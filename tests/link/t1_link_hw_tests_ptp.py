import pytest

# Split from t1_link_hw_tests.py because it needs 4+ snake pairs, one of them
# outside the first 5 flapped port IDs (see LinkTestRunner._gate_filters).
pytestmark = pytest.mark.topology("fboss-snake-4")

test_context = {
    "filters": [
        "*PtpTests*enablePtpPortDown*",
    ],
}


def test_t1_link_hw_tests_ptp(link_test_runner):
    assert link_test_runner.run_test(test_context)
