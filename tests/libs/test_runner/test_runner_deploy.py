"""Unit tests for BaseHwTestRunner._deploy_artifacts() and its helpers.

The orchestrator (TestInstanceFboss._resolve_artifact_urls) decides *what* to
use and sets per-stack env: a Nexis tarball URL (+ build_id) or a locally-built
CMake ``build/fboss`` dir.  The runner just consumes what it's handed for its
STACK — fetch+extract a tarball, or assemble from the local dir — then slices
and deploys to the DUT.
"""

import os
import re
import subprocess
import tarfile
from unittest.mock import MagicMock, patch

import pytest

from tests.libs.test_runner import runner as runner_module
from tests.libs.test_runner.runner import (
    BaseHwTestRunner,
    BenchmarkTestRunner,
    BspTestRunner,
    PlatformTestRunner,
    QsfpBenchmarkTestRunner,
    QsfpTestRunner,
    SaiAgentTestRunner,
    SaiTestRunner,
    SmokeTestRunner,
    _STACK_FORWARDING,
    _STACK_PLATFORM,
)

_FORWARDING_URL = "http://example/forwarding.tar.zst"

# Nexis env for a forwarding runner: tarball URL + build_id (the cache key).
_NEXIS_ENV = {
    "FBOSS_FORWARDING_TARBALL_URL": _FORWARDING_URL,
    "FBOSS_BUILD_ID": "12345",
}


@pytest.fixture
def isolated_cache(monkeypatch, tmp_path):
    """Point the host cache root at a per-test tmp dir so tests can't
    leak state into each other (or pollute the real /tmp/fboss-test-cache)."""
    cache_root = tmp_path / "fboss-test-cache"
    monkeypatch.setattr(runner_module, "_HOST_CACHE_ROOT", str(cache_root))
    return str(cache_root)


def _make_runner(runner_cls, deployed_sha: str | None = None):
    """Build a runner with SSH/SCP mocked.

    The DUT sha check runs `cat .../<Runner>.sha`; ``deployed_sha`` is what that
    returns (None → no marker file → cache miss → full deploy)."""
    runner = runner_cls()
    runner.ssh_client = MagicMock()
    runner.scp_client = MagicMock()
    runner.scp_client.put_file.return_value = (0, "ok")

    def ssh_handler(cmd, *args, **kwargs):
        if cmd.startswith("cat ") and ".sha" in cmd:
            return (0, deployed_sha + "\n") if deployed_sha is not None else (1, "")
        return (0, "ok")

    runner.ssh_client.run_cmd.side_effect = ssh_handler
    return runner


def _fake_run_factory(present_paths):
    """subprocess.run replacement for the Nexis path: wget downloads an empty
    tarball, `tar -xf` materializes ``present_paths`` in the extract dir.  The
    slice itself is packed with tarfile (no subprocess), so there's no -cf here."""
    recorded = {"calls": []}

    def fake_run(cmd, **kwargs):
        recorded["calls"].append(cmd)
        if cmd[0] == "wget" and "-O" in cmd:
            dest_path = cmd[cmd.index("-O") + 1]
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            with open(dest_path, "wb") as f:
                f.write(b"")
        elif cmd[0] == "tar" and "-xf" in cmd:
            extract_dir = cmd[2]
            for rel in present_paths:
                rel_clean = rel.rstrip("/")
                full = os.path.join(extract_dir, rel_clean)
                if rel.endswith("/"):
                    os.makedirs(full, exist_ok=True)
                else:
                    os.makedirs(os.path.dirname(full), exist_ok=True)
                    with open(full, "w") as f:
                        f.write("x")
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    return fake_run, recorded


class TestDeployArtifactsEnvValidation:
    def test_no_env_raises(self, isolated_cache):
        runner = _make_runner(SaiTestRunner)
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(RuntimeError, match="FBOSS_FORWARDING_LOCAL_DIR"):
                runner._deploy_artifacts()

    def test_url_without_build_id_raises(self, isolated_cache):
        runner = _make_runner(SaiTestRunner)
        with patch.dict(os.environ, {"FBOSS_FORWARDING_TARBALL_URL": _FORWARDING_URL}, clear=True):
            with pytest.raises(RuntimeError, match="FBOSS_BUILD_ID"):
                runner._deploy_artifacts()


class TestDeployArtifactsNexisHappyPath:
    def test_sai_runner_uploads_only_its_slice(self, monkeypatch, isolated_cache):
        runner = _make_runner(SaiTestRunner)
        fake_run, recorded = _fake_run_factory(SaiTestRunner.REQUIRED_PATHS)
        monkeypatch.setattr(subprocess, "run", fake_run)

        # Capture the archive paths in the tar that's actually SCP'd (the slice is
        # deleted right after upload, so inspect it from inside the put_file mock).
        packed_names = []

        def capture_put(local, remote, *a, **k):
            with tarfile.open(local) as t:
                packed_names.extend(t.getnames())
            return (0, "ok")

        runner.scp_client.put_file.side_effect = capture_put

        with patch.dict(os.environ, _NEXIS_ENV, clear=True):
            runner._deploy_artifacts()

        wget_calls = [c for c in recorded["calls"] if c[0] == "wget"]
        assert len(wget_calls) == 1
        assert _FORWARDING_URL in wget_calls[0]

        # The slice archive contains exactly this runner's REQUIRED_PATHS (each at
        # its on-DUT relative path) and nothing else from the full tarball.
        assert all(p.rstrip("/") in packed_names for p in SaiTestRunner.REQUIRED_PATHS)

        runner.scp_client.put_file.assert_called_once()
        _, remote_arg = runner.scp_client.put_file.call_args.args[:2]
        assert remote_arg == "/tmp/fboss-SaiTestRunner-slice.tar"

        # ssh calls: [cat <marker>, extract+record-sha, cleanup]
        extract_cmd = runner.ssh_client.run_cmd.call_args_list[1].args[0]
        assert "tar -C /opt/fboss -xf" in extract_cmd
        assert "/opt/fboss/.deployed/SaiTestRunner.sha" in extract_cmd
        assert "tee" in extract_cmd  # records the slice sha

    def test_platform_runner_uses_platform_url(self, monkeypatch, isolated_cache):
        runner = _make_runner(PlatformTestRunner)
        fake_run, recorded = _fake_run_factory(PlatformTestRunner.REQUIRED_PATHS)
        monkeypatch.setattr(subprocess, "run", fake_run)

        env = {
            "FBOSS_PLATFORM_TARBALL_URL": "http://example/platform.tar.zst",
            "FBOSS_FORWARDING_TARBALL_URL": "http://forwarding-should-not-be-used",
            "FBOSS_BUILD_ID": "12345",
        }
        with patch.dict(os.environ, env, clear=True):
            runner._deploy_artifacts()

        wget_calls = [c for c in recorded["calls"] if c[0] == "wget"]
        assert "http://example/platform.tar.zst" in wget_calls[0]
        assert all("forwarding-should-not-be-used" not in c for c in wget_calls)


class TestDeployArtifactsValidation:
    def test_missing_required_path_raises_loud_error(self, monkeypatch, isolated_cache):
        runner = _make_runner(SaiTestRunner)
        present = [p for p in SaiTestRunner.REQUIRED_PATHS if "sai_test-sai_impl" not in p]
        fake_run, _ = _fake_run_factory(present)
        monkeypatch.setattr(subprocess, "run", fake_run)

        with patch.dict(os.environ, _NEXIS_ENV, clear=True):
            with pytest.raises(RuntimeError, match="bin/sai_test-sai_impl"):
                runner._deploy_artifacts()
        runner.scp_client.put_file.assert_not_called()
        # validation runs before the sha check, so no DUT SSH happened yet
        assert runner.ssh_client.run_cmd.call_count == 0


class TestDeployArtifactsCleanup:
    def test_cleanup_runs_after_dut_extract_failure(self, monkeypatch, isolated_cache):
        runner = _make_runner(SaiTestRunner)

        def ssh_handler(cmd, *args, **kwargs):
            if cmd.startswith("cat ") and ".sha" in cmd:
                return (1, "")  # sha marker absent -> deploy
            if "tar -C /opt/fboss -xf" in cmd:
                return (1, "tar: corrupt archive")
            return (0, "ok")
        runner.ssh_client.run_cmd.side_effect = ssh_handler

        fake_run, _ = _fake_run_factory(SaiTestRunner.REQUIRED_PATHS)
        monkeypatch.setattr(subprocess, "run", fake_run)

        with patch.dict(os.environ, _NEXIS_ENV, clear=True):
            with pytest.raises(RuntimeError, match="Failed to extract slice tar"):
                runner._deploy_artifacts()

        cleanup_cmd = runner.ssh_client.run_cmd.call_args_list[-1].args[0]
        assert "rm -f /tmp/fboss-SaiTestRunner-slice.tar" in cleanup_cmd


class TestDeployArtifactsDutMarker:
    def test_sha_match_skips_scp(self, monkeypatch, isolated_cache):
        # DUT already records the sha of the slice we're about to pack.
        runner = _make_runner(SaiTestRunner, deployed_sha="deadbeef")
        monkeypatch.setattr(BaseHwTestRunner, "_sha256", staticmethod(lambda path: "deadbeef"))
        fake_run, recorded = _fake_run_factory(SaiTestRunner.REQUIRED_PATHS)
        monkeypatch.setattr(subprocess, "run", fake_run)

        with patch.dict(os.environ, _NEXIS_ENV, clear=True):
            runner._deploy_artifacts()

        # Host work (fetch+extract+pack) still happens, but the SCP + on-DUT
        # extract are skipped on a sha match.
        runner.scp_client.put_file.assert_not_called()
        assert runner.ssh_client.run_cmd.call_count == 1  # only the `cat` probe
        probe_cmd = runner.ssh_client.run_cmd.call_args.args[0]
        assert "cat /opt/fboss/.deployed/SaiTestRunner.sha" in probe_cmd


class TestDeployArtifactsCache:
    def test_second_deploy_same_build_id_skips_wget(self, monkeypatch, isolated_cache):
        runner_a = _make_runner(SaiTestRunner)
        runner_b = _make_runner(SaiTestRunner)
        fake_run, recorded = _fake_run_factory(SaiTestRunner.REQUIRED_PATHS)
        monkeypatch.setattr(subprocess, "run", fake_run)

        with patch.dict(os.environ, _NEXIS_ENV, clear=True):
            runner_a._deploy_artifacts()
            runner_b._deploy_artifacts()

        wget_calls = [c for c in recorded["calls"] if c[0] == "wget"]
        assert len(wget_calls) == 1  # second hit the extract cache


class TestCacheLifecycle:
    """The host cache is bounded to a single namespace."""

    def test_prune_removes_other_namespaces(self, isolated_cache):
        os.makedirs(os.path.join(isolated_cache, "old-build-1"))
        os.makedirs(os.path.join(isolated_cache, "old-build-2"))
        os.makedirs(os.path.join(isolated_cache, "12345"))
        _make_runner(SaiTestRunner)._prune_stale_cache("12345")
        assert os.listdir(isolated_cache) == ["12345"]

    def test_prune_noop_when_cache_absent(self, tmp_path, monkeypatch):
        monkeypatch.setattr(runner_module, "_HOST_CACHE_ROOT", str(tmp_path / "nope"))
        _make_runner(SaiTestRunner)._prune_stale_cache("12345")  # must not raise

    def test_deploy_prunes_stale_before_running(self, monkeypatch, isolated_cache):
        os.makedirs(os.path.join(isolated_cache, "old-build"))
        runner = _make_runner(SaiTestRunner)
        fake_run, _ = _fake_run_factory(SaiTestRunner.REQUIRED_PATHS)
        monkeypatch.setattr(subprocess, "run", fake_run)
        with patch.dict(os.environ, _NEXIS_ENV, clear=True):
            runner._deploy_artifacts()
        contents = os.listdir(isolated_cache)
        assert "old-build" not in contents  # stale build pruned
        assert "12345" in contents          # current build kept


class TestDeployArtifactsLocal:
    """Local path: orchestrator hands FBOSS_<STACK>_LOCAL_DIR; the runner packs
    the slice from the build dir (binaries) + repo (share/ configs)."""

    def _fake_repo_and_build(self, tmp_path):
        repo = tmp_path / "repo"
        oss = repo / "fboss" / "oss"
        # Every forwarding share dir a forwarding runner ships, so _slice_members
        # resolves a complete tree. share/platform_descriptors is special-cased in
        # _local_source_path (it lives outside fboss/oss/), so fake it there too.
        for rel in runner_module._STACK_SHARE[runner_module._STACK_FORWARDING]:
            rel_clean = rel.rstrip("/")
            if rel_clean == "share/platform_descriptors":
                d = repo / "fboss" / "lib" / "platform_mapping_v2" / "generated_platform_mappings"
            else:
                d = oss / rel_clean[len("share/"):]
            d.mkdir(parents=True, exist_ok=True)
            (d / "placeholder").write_text("cfg")
        build_fboss = tmp_path / "build" / "fboss"
        build_fboss.mkdir(parents=True)
        (build_fboss / "sai_test-sai_impl").write_text("ELF")
        return str(repo), str(build_fboss)

    def test_local_deploy_packs_and_uploads_slice(self, monkeypatch, isolated_cache, tmp_path):
        repo, build_fboss = self._fake_repo_and_build(tmp_path)
        runner = _make_runner(SaiTestRunner)

        packed_names = []

        def capture_put(local, remote, *a, **k):
            with tarfile.open(local) as t:
                packed_names.extend(t.getnames())
            return (0, "ok")

        runner.scp_client.put_file.side_effect = capture_put

        with patch.object(
            type(runner), "_fboss_repo_root",
            staticmethod(lambda: __import__("pathlib").Path(repo)),
        ):
            with patch.dict(os.environ, {"FBOSS_FORWARDING_LOCAL_DIR": build_fboss}, clear=True):
                runner._deploy_artifacts()

        # No subprocess at all on the local path — packed straight from disk.
        runner.scp_client.put_file.assert_called_once()
        _, remote_arg = runner.scp_client.put_file.call_args.args[:2]
        assert remote_arg == "/tmp/fboss-SaiTestRunner-slice.tar"
        # The binary (from the build dir) and a share config (from the repo) both
        # land in the slice at their on-DUT relative paths.
        assert "bin/sai_test-sai_impl" in packed_names
        assert any(n.startswith("share/hw_test_configs") for n in packed_names)
        # The DUT marker is the content sha, regardless of local vs Nexis source.
        extract_cmd = runner.ssh_client.run_cmd.call_args_list[1].args[0]
        assert "/opt/fboss/.deployed/SaiTestRunner.sha" in extract_cmd

    def test_local_missing_binary_raises(self, monkeypatch, isolated_cache, tmp_path):
        repo, build_fboss = self._fake_repo_and_build(tmp_path)
        os.remove(os.path.join(build_fboss, "sai_test-sai_impl"))  # dev didn't build it
        runner = _make_runner(SaiTestRunner)
        with patch.object(
            type(runner), "_fboss_repo_root",
            staticmethod(lambda: __import__("pathlib").Path(repo)),
        ):
            with patch.dict(os.environ, {"FBOSS_FORWARDING_LOCAL_DIR": build_fboss}, clear=True):
                with pytest.raises(RuntimeError, match="bin/sai_test-sai_impl"):
                    runner._deploy_artifacts()
        runner.scp_client.put_file.assert_not_called()


class TestLocalSourcePath:
    """_local_source_path mirrors package.py's test_files mapping."""

    def test_share_maps_to_oss(self, tmp_path):
        runner = _make_runner(SaiTestRunner)
        with patch.object(type(runner), "_fboss_repo_root", staticmethod(lambda: tmp_path)):
            got = runner._local_source_path("share/hw_test_configs", "/build/fboss")
        assert got == str(tmp_path / "fboss" / "oss" / "hw_test_configs")

    def test_platform_descriptors_maps_outside_oss(self, tmp_path):
        runner = _make_runner(SaiTestRunner)
        with patch.object(type(runner), "_fboss_repo_root", staticmethod(lambda: tmp_path)):
            got = runner._local_source_path("share/platform_descriptors", "/build/fboss")
        assert got == str(
            tmp_path / "fboss" / "lib" / "platform_mapping_v2" / "generated_platform_mappings"
        )

    def test_compiled_binary_maps_to_build_dir(self, tmp_path):
        runner = _make_runner(SaiTestRunner)
        with patch.object(type(runner), "_fboss_repo_root", staticmethod(lambda: tmp_path)):
            got = runner._local_source_path("bin/sai_test-sai_impl", "/build/fboss")
        assert got == os.path.join("/build/fboss", "sai_test-sai_impl")

    def test_run_script_maps_to_run_scripts(self, tmp_path):
        runner = _make_runner(PlatformTestRunner)
        with patch.object(type(runner), "_fboss_repo_root", staticmethod(lambda: tmp_path)):
            got = runner._local_source_path("bin/run_test.py", "/build/fboss")
        assert got == str(tmp_path / "fboss" / "oss" / "scripts" / "run_scripts" / "run_test.py")

    def test_python_test_maps_to_python_tests(self, tmp_path):
        runner = _make_runner(SaiTestRunner)
        with patch.object(type(runner), "_fboss_repo_root", staticmethod(lambda: tmp_path)):
            got = runner._local_source_path("bin/python_tests/agent_smoke.py", "/build/fboss")
        assert got == str(tmp_path / "fboss" / "oss" / "python_tests" / "agent_smoke.py")


class TestPlatformMappingPath:
    """_platform_mapping_path resolves both the legacy flat layout and the
    newer descriptor-backed <vendor>/<config>/ layout."""

    def _gen_dir(self, tmp_path):
        d = tmp_path / "fboss" / "lib" / "platform_mapping_v2" / "generated_platform_mappings"
        d.mkdir(parents=True, exist_ok=True)
        return d

    def test_flat_layout(self, tmp_path, monkeypatch):
        gen = self._gen_dir(tmp_path)
        flat = gen / "meru800bia_platform_mapping.json"
        flat.write_text("{}")
        monkeypatch.setattr(runner_module, "_repo_dir", lambda rel: gen)
        assert runner_module._platform_mapping_path("meru800bia") == flat

    def test_nested_vendor_layout(self, tmp_path, monkeypatch):
        gen = self._gen_dir(tmp_path)
        nested = gen / "accton" / "wedge800bact" / "platform_mapping.json"
        nested.parent.mkdir(parents=True)
        nested.write_text("{}")
        monkeypatch.setattr(runner_module, "_repo_dir", lambda rel: gen)
        assert runner_module._platform_mapping_path("wedge800bact") == nested

    def test_flat_preferred_over_nested(self, tmp_path, monkeypatch):
        gen = self._gen_dir(tmp_path)
        flat = gen / "foo_platform_mapping.json"
        flat.write_text("{}")
        nested = gen / "vendor" / "foo" / "platform_mapping.json"
        nested.parent.mkdir(parents=True)
        nested.write_text("{}")
        monkeypatch.setattr(runner_module, "_repo_dir", lambda rel: gen)
        assert runner_module._platform_mapping_path("foo") == flat

    def test_missing_raises(self, tmp_path, monkeypatch):
        gen = self._gen_dir(tmp_path)
        monkeypatch.setattr(runner_module, "_repo_dir", lambda rel: gen)
        with pytest.raises(FileNotFoundError):
            runner_module._platform_mapping_path("does_not_exist")


class TestLocalBuildFingerprint:
    """The local-build cache namespace fingerprints only the sources this runner
    uploads (its REQUIRED_PATHS), keyed on each file's (size, mtime_ns) — not the
    build dir's own mtime, which an in-place relink leaves untouched, and not the
    whole tree of binaries the runner doesn't ship."""

    def _runner_and_build(self, tmp_path):
        # Empty repo root → share/ + script sources resolve to nonexistent paths
        # and are skipped, isolating the fingerprint to the build-dir binary.
        d = tmp_path / "build" / "fboss"
        d.mkdir(parents=True)
        (d / "sai_test-sai_impl").write_text("ELF-v1")
        runner = _make_runner(SaiTestRunner)
        return runner, d, tmp_path / "repo"

    def _fp(self, runner, build_dir, repo):
        from pathlib import Path
        with patch.object(
            type(runner), "_fboss_repo_root", staticmethod(lambda: Path(repo))
        ):
            return runner._local_build_fingerprint(str(build_dir))

    def test_in_place_relink_changes_fingerprint(self, tmp_path):
        runner, d, repo = self._runner_and_build(tmp_path)
        binary = d / "sai_test-sai_impl"
        before = self._fp(runner, d, repo)

        # Simulate an in-place relink: same path/size, bumped mtime. The dir's own
        # mtime stays put (this is the failure mode the dir-mtime scheme missed).
        dir_mtime = os.stat(d).st_mtime_ns
        st = os.stat(binary)
        os.utime(binary, ns=(st.st_atime_ns, st.st_mtime_ns + 1_000_000))

        assert os.stat(d).st_mtime_ns == dir_mtime  # dir entry untouched
        assert self._fp(runner, d, repo) != before

    def test_content_size_change_changes_fingerprint(self, tmp_path):
        runner, d, repo = self._runner_and_build(tmp_path)
        before = self._fp(runner, d, repo)
        (d / "sai_test-sai_impl").write_text("ELF-v2-bigger")
        assert self._fp(runner, d, repo) != before

    def test_unrelated_binary_is_ignored(self, tmp_path):
        # A binary this runner doesn't upload changing must NOT bust the namespace
        # — that's the whole point of scoping to REQUIRED_PATHS.
        runner, d, repo = self._runner_and_build(tmp_path)
        before = self._fp(runner, d, repo)
        (d / "qsfp_hw_test").write_text("some other runner's binary")
        assert self._fp(runner, d, repo) == before

    def test_unbuilt_binary_is_skipped_not_fatal(self, tmp_path):
        # A REQUIRED_PATH the dev hasn't built yet is skipped here (the precise
        # error comes later from _slice_members), not a stat crash.
        runner, d, repo = self._runner_and_build(tmp_path)
        os.remove(d / "sai_test-sai_impl")
        assert self._fp(runner, d, repo)  # returns a digest, no exception

    def test_stable_when_nothing_changes(self, tmp_path):
        runner, d, repo = self._runner_and_build(tmp_path)
        assert self._fp(runner, d, repo) == self._fp(runner, d, repo)


class TestRunnerManifests:
    def test_sai_agent_runner_ships_production_features(self):
        assert "share/production_features/" in SaiAgentTestRunner.REQUIRED_PATHS

    def test_platform_runner_relies_on_image_for_run_test_py(self):
        # run_test.py + setup_fboss_env come from the production image on the DUT
        # (like the forwarding runners and BspTestRunner), so they aren't shipped.
        assert "bin/run_test.py" not in PlatformTestRunner.REQUIRED_PATHS

    def test_bsp_runner_does_not_need_run_test_py(self):
        assert "bin/run_test.py" not in BspTestRunner.REQUIRED_PATHS

    def test_benchmark_runner_has_a_deploy_manifest(self):
        assert BenchmarkTestRunner.STACK == _STACK_FORWARDING
        assert "bin/sai_all_benchmarks-sai_impl" in BenchmarkTestRunner.REQUIRED_PATHS

    def test_qsfp_benchmark_runner_has_a_deploy_manifest(self):
        assert QsfpBenchmarkTestRunner.STACK == _STACK_FORWARDING
        assert "bin/qsfp_hw_test_benchmark" in QsfpBenchmarkTestRunner.REQUIRED_PATHS
        # Must not inherit the SAI benchmark binary slice.
        assert "bin/sai_all_benchmarks-sai_impl" not in QsfpBenchmarkTestRunner.REQUIRED_PATHS

    def test_forwarding_runners_route_to_forwarding_stack(self):
        for cls in (SaiTestRunner, SaiAgentTestRunner, BenchmarkTestRunner, QsfpBenchmarkTestRunner):
            assert cls.STACK == _STACK_FORWARDING, f"{cls.__name__} should be forwarding"

    def test_platform_stack_runners_route_to_platform_stack(self):
        for cls in (PlatformTestRunner, BspTestRunner):
            assert cls.STACK == _STACK_PLATFORM, f"{cls.__name__} should be platform"


# run scripts and python smoke scripts ship under bin/ but aren't run_test.py
# gtest binaries, so they're excluded from the binary cross-check below.
_NON_BINARY_BIN = ("run_test.py", "setup_fboss_env")


def _declared_test_binaries(cls):
    """The run_test.py gtest binaries a runner deploys (bin/<name>), excluding
    run scripts (run_test.py/setup_fboss_env) and the python smoke scripts."""
    names = []
    for path in getattr(cls, "REQUIRED_PATHS", ()):
        if not path.startswith("bin/"):
            continue
        name = path[len("bin/"):]
        if name.endswith(".py") or name in _NON_BINARY_BIN:
            continue
        names.append(name)
    return names


def test_runner_binaries_are_known_to_fboss_test_runner():
    """Every gtest binary a runner deploys must be one the upstream test runner
    actually execs.

    The on-DUT runner is the upstream ``fboss_test_runner`` package (its
    ``runners/*.py`` _get_test_binary_name methods + ``constants.py``); it is the
    source of truth for binary names. Our per-runner BINARIES mirror that, so
    this guards against drift: a stale or mistyped binary name here, or upstream
    renaming/removing one, fails loudly with a pointer to reconcile.
    """
    pkg = (
        BaseHwTestRunner._fboss_repo_root()
        / "fboss/oss/scripts/run_scripts/fboss_test_runner"
    )
    tokens: set[str] = set()
    for py in pkg.rglob("*.py"):
        tokens |= set(re.findall(r"[A-Za-z0-9_.\-]+", py.read_text()))

    def _all_subclasses(cls):
        for sub in cls.__subclasses__():
            yield sub
            yield from _all_subclasses(sub)

    for cls in _all_subclasses(BaseHwTestRunner):
        for name in _declared_test_binaries(cls):
            assert name in tokens, (
                f"{cls.__name__} deploys bin/{name}, but the upstream "
                f"fboss_test_runner package never references it. Reconcile the "
                f"runner's BINARIES against fboss_test_runner/runners/*.py — it "
                f"is the source of truth for binary names."
            )


class TestDeployOnly:
    """FBOSS_DEPLOY_ONLY (set by nhtests-run --mode deploy): run_test() deploys
    this runner's slice via setup() then returns without executing the test."""

    def _patch_clients(self, monkeypatch):
        """Make setup() build mock SSH/SCP clients instead of real ones.

        setup() reassigns self.ssh_client/scp_client to fresh Device*Clients, so
        (unlike the _deploy_artifacts tests) we must patch the classes the
        runner module imported, not the instance attributes.
        """
        ssh = MagicMock()
        scp = MagicMock()
        scp.put_file.return_value = (0, "ok")

        def ssh_handler(cmd, *args, **kwargs):
            # marker-probe miss → full deploy path runs
            if "test -f" in cmd and "test -e" in cmd:
                return (1, "")
            return (0, "ok")

        ssh.run_cmd.side_effect = ssh_handler
        monkeypatch.setattr(runner_module, "DeviceSSHClient", lambda *a, **k: ssh)
        monkeypatch.setattr(runner_module, "DeviceSCPClient", lambda *a, **k: scp)
        return ssh, scp

    def test_run_test_deploys_then_skips_execution(self, monkeypatch, isolated_cache):
        ssh, scp = self._patch_clients(monkeypatch)
        fake_run, _ = _fake_run_factory(SaiTestRunner.REQUIRED_PATHS)
        monkeypatch.setattr(subprocess, "run", fake_run)

        runner = SaiTestRunner()
        env = dict(_NEXIS_ENV)
        env["FBOSS_DEPLOY_ONLY"] = "1"
        with patch.dict(os.environ, env):
            result = runner.run_test({})

        # Returns success without running the binary.
        assert result is True

        # Deploy still happened: the slice was SCP'd to the DUT.
        scp.put_file.assert_called_once()
        assert scp.put_file.call_args.args[1] == "/tmp/fboss-SaiTestRunner-slice.tar"

        # Test was NOT executed: run_test.py never invoked, no results fetched.
        assert all("run_test.py" not in c.args[0] for c in ssh.run_cmd.call_args_list)
        scp.get_file.assert_not_called()

    def test_run_test_deploy_failure_propagates(self, monkeypatch, isolated_cache):
        """A failed upload must NOT be swallowed into a success. The SCP failure
        raises out of setup()/_deploy_artifacts() (before the deploy-only
        early-return), so run_test() raises — failing the pytest test (exit 1),
        which nhtests-run maps to FAIL_ENV instead of a false PASS."""
        ssh, scp = self._patch_clients(monkeypatch)
        scp.put_file.return_value = (1, "scp: permission denied")  # upload fails
        fake_run, _ = _fake_run_factory(SaiTestRunner.REQUIRED_PATHS)
        monkeypatch.setattr(subprocess, "run", fake_run)

        runner = SaiTestRunner()
        env = dict(_NEXIS_ENV)
        env["FBOSS_DEPLOY_ONLY"] = "1"
        with patch.dict(os.environ, env):
            with pytest.raises(RuntimeError, match="Failed to copy slice tar"):
                runner.run_test({})

        # Never reached the deploy-only skip / success return.
        assert all("run_test.py" not in c.args[0] for c in ssh.run_cmd.call_args_list)

    def test_run_test_without_deploy_only_executes(self, monkeypatch, isolated_cache):
        """Sanity counterpart: with the env var unset, run_test() proceeds past
        deploy and runs the binary on the DUT (run_test.py is invoked)."""
        ssh, scp = self._patch_clients(monkeypatch)
        scp.get_file.return_value = (0, "ok")
        fake_run, _ = _fake_run_factory(SaiTestRunner.REQUIRED_PATHS)
        monkeypatch.setattr(subprocess, "run", fake_run)

        runner = SaiTestRunner()
        env = {k: v for k, v in _NEXIS_ENV.items()}
        env["DUT"] = "dut-1"
        env["HWSKU"] = "minipack3"
        # Ensure FBOSS_DEPLOY_ONLY is absent.
        with patch.dict(os.environ, env, clear=False):
            os.environ.pop("FBOSS_DEPLOY_ONLY", None)
            runner.run_test({"filters": []})

        assert any("run_test.py" in c.args[0] for c in ssh.run_cmd.call_args_list)

    def test_smoke_runner_honors_deploy_only(self, monkeypatch, isolated_cache):
        """SmokeTestRunner customizes execution via _run_test_impl, so the
        deploy-only gate in the base run_test() applies to it too: the slice is
        deployed but agent_smoke.py never runs. (Regression: when the gate lived
        in a run_test() that SmokeTestRunner overrode, it was silently skipped.)"""
        ssh, scp = self._patch_clients(monkeypatch)
        fake_run, _ = _fake_run_factory(SmokeTestRunner.REQUIRED_PATHS)
        monkeypatch.setattr(subprocess, "run", fake_run)

        runner = SmokeTestRunner()
        env = dict(_NEXIS_ENV)
        env["FBOSS_DEPLOY_ONLY"] = "1"
        with patch.dict(os.environ, env):
            result = runner.run_test({})

        assert result is True
        scp.put_file.assert_called_once()  # deploy still happened
        assert all("agent_smoke.py" not in c.args[0] for c in ssh.run_cmd.call_args_list)

    def test_benchmark_runner_honors_deploy_only(self, monkeypatch, isolated_cache):
        """BenchmarkTestRunner's _run_test_impl runs only after the base
        run_test() clears the deploy-only gate, so in deploy-only mode no
        benchmark runs and the CSV/tr.xml post-processing is skipped entirely.
        (Regression: it used to call super().run_test(), get an early True, then
        fail in CSV post-processing — a false failure plus a padding sleep.)"""
        ssh, scp = self._patch_clients(monkeypatch)
        fake_run, _ = _fake_run_factory(BenchmarkTestRunner.REQUIRED_PATHS)
        monkeypatch.setattr(subprocess, "run", fake_run)

        runner = BenchmarkTestRunner()
        env = dict(_NEXIS_ENV)
        env["FBOSS_DEPLOY_ONLY"] = "1"
        with patch.dict(os.environ, env):
            result = runner.run_test({})

        assert result is True
        scp.put_file.assert_called_once()  # deploy still happened
        # Neither the benchmark run nor its result fetch happened.
        assert all("run_test.py" not in c.args[0] for c in ssh.run_cmd.call_args_list)
        scp.get_file.assert_not_called()

    def test_qsfp_runner_honors_deploy_only_on_cabling_path(
        self, monkeypatch, isolated_cache
    ):
        """QsfpTestRunner overrides _run_test_impl (not run_test), so the base
        run_test() deploy-only gate fires before the cabling-aware path is ever
        reached: the slice is deployed but no QSFP pass runs. (Regression: when
        QsfpTestRunner overrode run_test() and routed the cabled DUT straight
        into _run_cabling_aware, --mode deploy silently executed the tests.)"""
        ssh, scp = self._patch_clients(monkeypatch)
        fake_run, _ = _fake_run_factory(QsfpTestRunner.REQUIRED_PATHS)
        monkeypatch.setattr(subprocess, "run", fake_run)

        runner = QsfpTestRunner()
        env = dict(_NEXIS_ENV)
        env["FBOSS_DEPLOY_ONLY"] = "1"
        env["TEST_PORTS_INFO"] = "/does/not/matter"  # gate must win before this
        with patch.dict(os.environ, env):
            result = runner.run_test({})

        assert result is True
        scp.put_file.assert_called_once()  # deploy still happened
        assert all("run_test.py" not in c.args[0] for c in ssh.run_cmd.call_args_list)
        scp.get_file.assert_not_called()
