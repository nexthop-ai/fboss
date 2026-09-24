"""4x200G breakout variant of t1_qsfp_hw_tests.py:
unsupported pairs are excluded and a platform with no supported pair reports SKIP."""

from tests.qsfp.t1_qsfp_hw_tests import test_context as _base_context

test_context = {**_base_context, "variant": "4x200G"}


def test_t1_qsfp_hw_tests_4x200g(qsfp_test_runner):
    assert qsfp_test_runner.run_test(test_context)
