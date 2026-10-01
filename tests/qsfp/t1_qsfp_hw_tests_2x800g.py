"""2x800G breakout variant of t1_qsfp_hw_tests.py:
unsupported pairs are excluded and a platform with no supported pair reports SKIP."""

import pytest

from tests.qsfp.t1_qsfp_hw_tests import test_context as _base_context

pytestmark = pytest.mark.topology("fboss-has-xcvrs")

test_context = {**_base_context, "variant": "2x800G"}


def test_t1_qsfp_hw_tests_2x800g(qsfp_test_runner):
    assert qsfp_test_runner.run_test(test_context)
