import logging
import pytest

from tests.libs.test_runner.runner import (
    LinkTestRunner,
    QsfpTestRunner,
    SaiAgentTestRunner,
    SaiTestRunner,
)


def pytest_configure(config):
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s: %(message)s",
        datefmt="%H:%M:%S"
    )


@pytest.fixture
def sai_test_runner():
    """Fixture for SAI hardware tests."""
    runner = SaiTestRunner()
    yield runner
    runner.close()


@pytest.fixture
def sai_agent_test_runner():
    """Fixture for SAI agent tests."""
    runner = SaiAgentTestRunner()
    yield runner
    runner.close()


@pytest.fixture
def qsfp_test_runner():
    """Fixture for QSFP hardware tests."""
    runner = QsfpTestRunner()
    yield runner
    runner.close()


@pytest.fixture
def link_test_runner():
    """Fixture for link tests."""
    runner = LinkTestRunner()
    yield runner
    runner.close()
