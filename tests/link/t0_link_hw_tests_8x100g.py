"""8x100G breakout variant of t0_link_hw_tests.py:
unsupported pairs are excluded and a platform with no supported pair reports SKIP."""

from tests.link.t0_link_hw_tests import test_context as _base_context

test_context = {**_base_context, "variant": "8x100G"}


def test_t0_link_hw_tests_8x100g(link_test_runner):
    assert link_test_runner.run_test(test_context)
