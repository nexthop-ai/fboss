import logging
import pytest

from tests.libs.test_runner.runner import (
    BspTestRunner,
    LinkTestRunner,
    PlatformTestRunner,
    QsfpTestRunner,
    SaiAgentTestRunner,
    SaiTestRunner,
    SmokeTestRunner,
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


@pytest.fixture
def platform_hw_test_runner():
    """Fixture for platform hardware tests."""
    runner = PlatformTestRunner("platform_hw_test")
    yield runner
    runner.close()


@pytest.fixture
def fan_service_hw_test_runner():
    """Fixture for fan service hardware tests."""
    runner = PlatformTestRunner("fan_service_hw_test")
    yield runner
    runner.close()


@pytest.fixture
def sensor_service_hw_test_runner():
    """Fixture for sensor service hardware tests."""
    runner = PlatformTestRunner("sensor_service_hw_test")
    yield runner
    runner.close()


@pytest.fixture
def fw_util_hw_test_runner():
    """Fixture for firmware utility hardware tests."""
    runner = PlatformTestRunner("fw_util_hw_test")
    yield runner
    runner.close()


@pytest.fixture
def weutil_hw_test_runner():
    """Fixture for weutil hardware tests."""
    runner = PlatformTestRunner("weutil_hw_test")
    yield runner
    runner.close()


@pytest.fixture
def data_corral_service_hw_test_runner():
    """Fixture for data corral service hardware tests."""
    runner = PlatformTestRunner("data_corral_service_hw_test")
    yield runner
    runner.close()


@pytest.fixture
def platform_manager_hw_test_runner():
    """Fixture for platform manager hardware tests."""
    runner = PlatformTestRunner("platform_manager_hw_test")
    yield runner
    runner.close()


@pytest.fixture
def bsp_test_runner():
    """Fixture for BSP hardware tests."""
    runner = BspTestRunner()
    yield runner
    runner.close()


@pytest.fixture
def smoke_test_runner():
    """Fixture for FBOSS daemon smoke tests."""
    runner = SmokeTestRunner()
    yield runner
    runner.close()
