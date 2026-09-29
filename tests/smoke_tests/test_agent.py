import pytest

pytestmark = pytest.mark.topology("fboss-standalone")


def test_daemons_smoke(smoke_test_runner):
    assert smoke_test_runner.run_test({})
