"""2x400G breakout variant of t0_qsfp_hw_tests.py:
unsupported pairs are excluded and a platform with no supported pair reports SKIP."""

from tests.qsfp.t0_qsfp_hw_tests import test_context as _base_context

test_context = {**_base_context, "variant": "2x400G"}


def test_t0_qsfp_hw_tests_2x400g(qsfp_test_runner):
    assert qsfp_test_runner.run_test(test_context)
