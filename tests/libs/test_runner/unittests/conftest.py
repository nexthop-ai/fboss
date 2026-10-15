import pytest

from tests.libs.test_runner import deploy as deploy_module
from tests.libs.test_runner import platform_mapping, variants

from .helpers import LANES_BY_ID, MEDIUM_BY_ID


@pytest.fixture(autouse=True)
def _clear_profile_caches():
    """The thrift-derived profile tables are module-level lru_caches; drop them
    around every test so a stubbed or real parse never leaks into the next."""

    def clear():
        for name in ("_profile_lanes_by_id", "_profile_medium_by_id"):
            fn = getattr(platform_mapping, name)
            if hasattr(fn, "cache_clear"):
                fn.cache_clear()

    clear()
    yield
    clear()


@pytest.fixture
def isolated_cache(monkeypatch, tmp_path):
    """Point the host cache root at a per-test tmp dir so tests can't
    leak state into each other (or pollute the real /tmp/fboss-test-cache)."""
    cache_root = tmp_path / "fboss-test-cache"
    monkeypatch.setattr(deploy_module, "_HOST_CACHE_ROOT", str(cache_root))
    return str(cache_root)


@pytest.fixture
def profile_tables(monkeypatch):
    """Stub the thrift-derived profile tables with the helpers.PROFILES set.
    variants.py binds _profile_medium_by_id by name, so it is patched too."""
    monkeypatch.setattr(platform_mapping, "_profile_medium_by_id", lambda: MEDIUM_BY_ID)
    monkeypatch.setattr(platform_mapping, "_profile_lanes_by_id", lambda: LANES_BY_ID)
    monkeypatch.setattr(variants, "_profile_medium_by_id", lambda: MEDIUM_BY_ID)
