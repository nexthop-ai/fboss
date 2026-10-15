"""ArtifactDeployer, driven through BaseHwTestRunner._deploy_artifacts().

The orchestrator (TestInstanceFboss._resolve_artifact_urls) decides *what* to
use and sets per-stack env: a Nexis tarball URL (+ build_id) or a locally-built
CMake ``build/fboss`` dir.  The runner just consumes what it's handed for its
STACK (fetch and extract a tarball, or assemble from the local dir), then slices
and deploys to the DUT.
"""

import os
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from tests.libs.test_runner import PlatformTestRunner, SaiTestRunner
from tests.libs.test_runner import deploy as deploy_module
from tests.libs.test_runner.deploy import (
    STACK_FORWARDING,
    STACK_SHARE,
    ArtifactDeployer,
)

from .helpers import FORWARDING_URL, NEXIS_ENV, capture_tar_names, fake_run_factory, make_runner


class TestDeployArtifactsEnvValidation:
    def test_no_env_raises(self, isolated_cache):
        runner = make_runner(SaiTestRunner)
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(RuntimeError, match="FBOSS_FORWARDING_LOCAL_DIR"):
                runner._deploy_artifacts()

    def test_url_without_build_id_raises(self, isolated_cache):
        runner = make_runner(SaiTestRunner)
        with patch.dict(os.environ, {"FBOSS_FORWARDING_TARBALL_URL": FORWARDING_URL}, clear=True):
            with pytest.raises(RuntimeError, match="FBOSS_BUILD_ID"):
                runner._deploy_artifacts()


class TestDeployArtifactsNexisHappyPath:
    def test_sai_runner_uploads_only_its_slice(self, monkeypatch, isolated_cache):
        runner = make_runner(SaiTestRunner)
        fake_run, recorded = fake_run_factory(SaiTestRunner.REQUIRED_PATHS)
        monkeypatch.setattr(subprocess, "run", fake_run)

        packed_names = capture_tar_names(runner)

        with patch.dict(os.environ, NEXIS_ENV, clear=True):
            runner._deploy_artifacts()

        wget_calls = [c for c in recorded["calls"] if c[0] == "wget"]
        assert len(wget_calls) == 1
        assert FORWARDING_URL in wget_calls[0]

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
        runner = make_runner(PlatformTestRunner)
        fake_run, recorded = fake_run_factory(PlatformTestRunner.REQUIRED_PATHS)
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
        runner = make_runner(SaiTestRunner)
        present = [p for p in SaiTestRunner.REQUIRED_PATHS if "sai_test-sai_impl" not in p]
        fake_run, _ = fake_run_factory(present)
        monkeypatch.setattr(subprocess, "run", fake_run)

        with patch.dict(os.environ, NEXIS_ENV, clear=True):
            with pytest.raises(RuntimeError, match="bin/sai_test-sai_impl"):
                runner._deploy_artifacts()
        runner.scp_client.put_file.assert_not_called()
        # validation runs before the sha check, so no DUT SSH happened yet
        assert runner.ssh_client.run_cmd.call_count == 0


class TestDeployArtifactsCleanup:
    def test_cleanup_runs_after_dut_extract_failure(self, monkeypatch, isolated_cache):
        runner = make_runner(SaiTestRunner)

        def ssh_handler(cmd, *args, **kwargs):
            if cmd.startswith("cat ") and ".sha" in cmd:
                return (1, "")  # sha marker absent -> deploy
            if "tar -C /opt/fboss -xf" in cmd:
                return (1, "tar: corrupt archive")
            return (0, "ok")
        runner.ssh_client.run_cmd.side_effect = ssh_handler

        fake_run, _ = fake_run_factory(SaiTestRunner.REQUIRED_PATHS)
        monkeypatch.setattr(subprocess, "run", fake_run)

        with patch.dict(os.environ, NEXIS_ENV, clear=True):
            with pytest.raises(RuntimeError, match="Failed to extract slice tar"):
                runner._deploy_artifacts()

        cleanup_cmd = runner.ssh_client.run_cmd.call_args_list[-1].args[0]
        assert "rm -f /tmp/fboss-SaiTestRunner-slice.tar" in cleanup_cmd


class TestDeployArtifactsDutMarker:
    def test_sha_match_skips_scp(self, monkeypatch, isolated_cache):
        # DUT already records the sha of the slice we're about to pack.
        runner = make_runner(SaiTestRunner, deployed_sha="deadbeef")
        monkeypatch.setattr(ArtifactDeployer, "_sha256", staticmethod(lambda path: "deadbeef"))
        fake_run, _ = fake_run_factory(SaiTestRunner.REQUIRED_PATHS)
        monkeypatch.setattr(subprocess, "run", fake_run)

        with patch.dict(os.environ, NEXIS_ENV, clear=True):
            runner._deploy_artifacts()

        # Host work (fetch+extract+pack) still happens, but the SCP + on-DUT
        # extract are skipped on a sha match.
        runner.scp_client.put_file.assert_not_called()
        assert runner.ssh_client.run_cmd.call_count == 1  # only the `cat` probe
        probe_cmd = runner.ssh_client.run_cmd.call_args.args[0]
        assert "cat /opt/fboss/.deployed/SaiTestRunner.sha" in probe_cmd


class TestDeployArtifactsCache:
    def test_second_deploy_same_build_id_skips_wget(self, monkeypatch, isolated_cache):
        runner_a = make_runner(SaiTestRunner)
        runner_b = make_runner(SaiTestRunner)
        fake_run, recorded = fake_run_factory(SaiTestRunner.REQUIRED_PATHS)
        monkeypatch.setattr(subprocess, "run", fake_run)

        with patch.dict(os.environ, NEXIS_ENV, clear=True):
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
        ArtifactDeployer._prune_stale_cache("12345")
        assert os.listdir(isolated_cache) == ["12345"]

    def test_prune_noop_when_cache_absent(self, tmp_path, monkeypatch):
        monkeypatch.setattr(deploy_module, "_HOST_CACHE_ROOT", str(tmp_path / "nope"))
        ArtifactDeployer._prune_stale_cache("12345")  # must not raise

    def test_deploy_prunes_stale_before_running(self, monkeypatch, isolated_cache):
        os.makedirs(os.path.join(isolated_cache, "old-build"))
        runner = make_runner(SaiTestRunner)
        fake_run, _ = fake_run_factory(SaiTestRunner.REQUIRED_PATHS)
        monkeypatch.setattr(subprocess, "run", fake_run)
        with patch.dict(os.environ, NEXIS_ENV, clear=True):
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
        # resolves a complete tree.
        for rel in STACK_SHARE[STACK_FORWARDING]:
            rel_clean = rel.rstrip("/")
            d = oss / rel_clean[len("share/"):]
            d.mkdir(parents=True, exist_ok=True)
            (d / "placeholder").write_text("cfg")
        build_fboss = tmp_path / "build" / "fboss"
        build_fboss.mkdir(parents=True)
        (build_fboss / "sai_test-sai_impl").write_text("ELF")
        return str(repo), str(build_fboss)

    def test_local_deploy_packs_and_uploads_slice(self, monkeypatch, isolated_cache, tmp_path):
        repo, build_fboss = self._fake_repo_and_build(tmp_path)
        runner = make_runner(SaiTestRunner)

        packed_names = capture_tar_names(runner)

        with patch.object(ArtifactDeployer, "_fboss_repo_root", staticmethod(lambda: Path(repo))):
            with patch.dict(os.environ, {"FBOSS_FORWARDING_LOCAL_DIR": build_fboss}, clear=True):
                runner._deploy_artifacts()

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
        runner = make_runner(SaiTestRunner)
        with patch.object(ArtifactDeployer, "_fboss_repo_root", staticmethod(lambda: Path(repo))):
            with patch.dict(os.environ, {"FBOSS_FORWARDING_LOCAL_DIR": build_fboss}, clear=True):
                with pytest.raises(RuntimeError, match="bin/sai_test-sai_impl"):
                    runner._deploy_artifacts()
        runner.scp_client.put_file.assert_not_called()


def _make_deployer(runner_cls):
    return ArtifactDeployer(
        runner_name=runner_cls.__name__,
        stack=runner_cls.STACK,
        required_paths=runner_cls.REQUIRED_PATHS,
        ssh_client=MagicMock(),
        scp_client=MagicMock(),
    )


class TestLocalSourcePath:
    """_local_source_path mirrors package.py's test_files mapping."""

    def test_share_maps_to_oss(self, tmp_path):
        deployer = _make_deployer(SaiTestRunner)
        with patch.object(ArtifactDeployer, "_fboss_repo_root", staticmethod(lambda: tmp_path)):
            got = deployer._local_source_path("share/hw_test_configs", "/build/fboss")
        assert got == str(tmp_path / "fboss" / "oss" / "hw_test_configs")

    def test_compiled_binary_maps_to_build_dir(self, tmp_path):
        deployer = _make_deployer(SaiTestRunner)
        with patch.object(ArtifactDeployer, "_fboss_repo_root", staticmethod(lambda: tmp_path)):
            got = deployer._local_source_path("bin/sai_test-sai_impl", "/build/fboss")
        assert got == os.path.join("/build/fboss", "sai_test-sai_impl")

    def test_run_script_maps_to_run_scripts(self, tmp_path):
        deployer = _make_deployer(PlatformTestRunner)
        with patch.object(ArtifactDeployer, "_fboss_repo_root", staticmethod(lambda: tmp_path)):
            got = deployer._local_source_path("bin/run_test.py", "/build/fboss")
        assert got == str(tmp_path / "fboss" / "oss" / "scripts" / "run_scripts" / "run_test.py")

    def test_python_test_maps_to_python_tests(self, tmp_path):
        deployer = _make_deployer(SaiTestRunner)
        with patch.object(ArtifactDeployer, "_fboss_repo_root", staticmethod(lambda: tmp_path)):
            got = deployer._local_source_path("bin/python_tests/agent_smoke.py", "/build/fboss")
        assert got == str(tmp_path / "fboss" / "oss" / "python_tests" / "agent_smoke.py")


class TestLocalBuildFingerprint:
    """The local-build cache namespace fingerprints only the sources this runner
    uploads (its REQUIRED_PATHS), keyed on each file's (size, mtime_ns): not the
    build dir's own mtime, which an in-place relink leaves untouched, and not the
    whole tree of binaries the runner doesn't ship."""

    @staticmethod
    def _build_dir(tmp_path):
        d = tmp_path / "build" / "fboss"
        d.mkdir(parents=True)
        (d / "sai_test-sai_impl").write_text("ELF-v1")
        return d

    @staticmethod
    def _fp(build_dir, repo):
        # An empty repo root makes the share/ and script sources resolve to
        # nothing, so the fingerprint covers the build-dir binary alone.
        deployer = _make_deployer(SaiTestRunner)
        with patch.object(ArtifactDeployer, "_fboss_repo_root", staticmethod(lambda: Path(repo))):
            return deployer._local_build_fingerprint(str(build_dir))

    def test_in_place_relink_changes_fingerprint(self, tmp_path):
        d, repo = self._build_dir(tmp_path), tmp_path / "repo"
        binary = d / "sai_test-sai_impl"
        before = self._fp(d, repo)

        # Simulate an in-place relink: same path/size, bumped mtime. The dir's own
        # mtime stays put (this is the failure mode the dir-mtime scheme missed).
        dir_mtime = os.stat(d).st_mtime_ns
        st = os.stat(binary)
        os.utime(binary, ns=(st.st_atime_ns, st.st_mtime_ns + 1_000_000))

        assert os.stat(d).st_mtime_ns == dir_mtime  # dir entry untouched
        assert self._fp(d, repo) != before

    def test_content_size_change_changes_fingerprint(self, tmp_path):
        d, repo = self._build_dir(tmp_path), tmp_path / "repo"
        before = self._fp(d, repo)
        (d / "sai_test-sai_impl").write_text("ELF-v2-bigger")
        assert self._fp(d, repo) != before

    def test_unrelated_binary_is_ignored(self, tmp_path):
        # A binary this runner doesn't upload changing must not bust the namespace,
        # by design, since the fingerprint is scoped to REQUIRED_PATHS.
        d, repo = self._build_dir(tmp_path), tmp_path / "repo"
        before = self._fp(d, repo)
        (d / "qsfp_hw_test").write_text("some other runner's binary")
        assert self._fp(d, repo) == before

    def test_unbuilt_binary_is_skipped_not_fatal(self, tmp_path):
        # A REQUIRED_PATH the dev hasn't built yet is skipped here (the precise
        # error comes later from _slice_members), not a stat crash.
        d, repo = self._build_dir(tmp_path), tmp_path / "repo"
        os.remove(d / "sai_test-sai_impl")
        assert self._fp(d, repo)  # returns a digest, no exception

    def test_stable_when_nothing_changes(self, tmp_path):
        d, repo = self._build_dir(tmp_path), tmp_path / "repo"
        assert self._fp(d, repo) == self._fp(d, repo)
