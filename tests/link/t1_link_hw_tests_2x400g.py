"""2x400G breakout variant of t1_link_hw_tests.py:
unsupported pairs are excluded and a platform with no supported pair reports SKIP."""

import pytest

from tests.link.t1_link_hw_tests import test_context as _base_context

pytestmark = pytest.mark.topology("fboss-snake")

test_context = {**_base_context, "variant": "2x400G"}


def test_t1_link_hw_tests_2x400g(link_test_runner):
    assert link_test_runner.run_test(test_context)
