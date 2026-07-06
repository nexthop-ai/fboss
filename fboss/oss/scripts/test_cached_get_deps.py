#!/usr/bin/env python3
"""Unit tests for cached-get-deps.py.

Tests are self-contained: they mock all network and subprocess calls and do
not build any real FBOSS or getdeps targets.
"""

from __future__ import annotations

import importlib.util
import io
import json
import os
import tempfile
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from unittest.mock import MagicMock, patch

# Load cached-get-deps as a module (it's not a package, and has hyphens in the name).
_SCRIPT = str(Path(__file__).resolve().parent / "cached-get-deps.py")
_spec = importlib.util.spec_from_file_location("cached_get_deps", _SCRIPT)
cgd = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cgd)


# ---------------------------------------------------------------------------
# _DEFAULT_CMAKE_DEFINES consistency
# ---------------------------------------------------------------------------


class TestDefaultCmakeDefines(unittest.TestCase):
    """The _DEFAULT_CMAKE_DEFINES dict must contain the right keys and be
    serialised identically wherever it is used, so that getdeps computes the
    same hash whether called from create_loader() or from the subprocess."""

    def test_build_shared_libs_is_off(self):
        """BUILD_SHARED_LIBS=OFF is required to override glog's manifest which
        sets BUILD_SHARED_LIBS=ON, so all deps produce static archives."""
        self.assertEqual(cgd._DEFAULT_CMAKE_DEFINES.get("BUILD_SHARED_LIBS"), "OFF")

    def test_range_v3_tests_disabled(self):
        self.assertEqual(cgd._DEFAULT_CMAKE_DEFINES.get("RANGE_V3_TESTS"), "OFF")
        self.assertEqual(cgd._DEFAULT_CMAKE_DEFINES.get("RANGE_V3_PERF"), "OFF")

    def test_json_roundtrip_is_stable(self):
        """_DEFAULT_CMAKE_DEFINES_JSON must be exactly json.dumps(_DEFAULT_CMAKE_DEFINES),
        so create_loader() and the subprocess both set GETDEPS_CMAKE_DEFINES to
        the identical string and compute matching project hashes."""
        expected = json.dumps(cgd._DEFAULT_CMAKE_DEFINES)
        self.assertEqual(cgd._DEFAULT_CMAKE_DEFINES_JSON, expected)

    def test_build_single_dep_passes_defines_to_subprocess(self):
        """build_single_dep() must pass --extra-cmake-defines=<JSON> to the
        getdeps.py subprocess so its hash matches the one computed by
        create_loader()."""
        mock_opts = MagicMock()
        mock_opts.scratch_dir = "/tmp/scratch"
        mock_manifest = MagicMock()
        mock_loader = MagicMock()
        mock_loader.load_manifest.return_value = mock_manifest
        mock_loader.get_project_install_dir.return_value = (
            "/tmp/scratch/installed/gflags-abc"
        )
        mock_loader.get_project_hash.return_value = "abc123"
        defines = cgd._DEFAULT_CMAKE_DEFINES_JSON

        with (
            patch.object(cgd.subprocess, "run") as mock_run,
            patch.object(cgd.os.path, "exists", return_value=False),
        ):
            mock_run.return_value = MagicMock(returncode=0)
            cgd.build_single_dep(
                mock_opts, mock_loader, "gflags", defines, "MinSizeRel", None
            )

        self.assertEqual(mock_run.call_count, 1)
        cmd = mock_run.call_args[0][0]
        defines_arg = f"--extra-cmake-defines={defines}"
        self.assertIn(
            defines_arg, cmd, f"subprocess cmd must include {defines_arg!r}; got {cmd}"
        )

    def test_build_single_dep_passes_build_type_to_subprocess(self):
        """build_single_dep() must forward --build-type to getdeps subprocess."""
        mock_opts = MagicMock()
        mock_opts.scratch_dir = "/tmp/scratch"
        mock_loader = MagicMock()
        mock_loader.get_project_install_dir.return_value = "/tmp/inst/gflags"
        mock_loader.get_project_hash.return_value = "abc123"

        with (
            patch.object(cgd.subprocess, "run") as mock_run,
            patch.object(cgd.os.path, "exists", return_value=False),
        ):
            mock_run.return_value = MagicMock(returncode=0)
            cgd.build_single_dep(
                mock_opts,
                mock_loader,
                "gflags",
                cgd._DEFAULT_CMAKE_DEFINES_JSON,
                "Debug",
                None,
            )

        cmd = mock_run.call_args[0][0]
        self.assertIn("--build-type", cmd)
        build_type_idx = cmd.index("--build-type")
        self.assertEqual(cmd[build_type_idx + 1], "Debug")

    def test_build_single_dep_passes_num_jobs_to_subprocess(self):
        """build_single_dep() must forward --num-jobs when provided."""
        mock_opts = MagicMock()
        mock_opts.scratch_dir = "/tmp/scratch"
        mock_loader = MagicMock()
        mock_loader.get_project_install_dir.return_value = "/tmp/inst/gflags"
        mock_loader.get_project_hash.return_value = "abc123"

        with (
            patch.object(cgd.subprocess, "run") as mock_run,
            patch.object(cgd.os.path, "exists", return_value=False),
        ):
            mock_run.return_value = MagicMock(returncode=0)
            cgd.build_single_dep(
                mock_opts,
                mock_loader,
                "gflags",
                cgd._DEFAULT_CMAKE_DEFINES_JSON,
                "MinSizeRel",
                8,
            )

        cmd = mock_run.call_args[0][0]
        self.assertIn("--num-jobs", cmd)
        idx = cmd.index("--num-jobs")
        self.assertEqual(cmd[idx + 1], "8")

    def test_create_loader_passes_defines_to_setup_build_options(self):
        """create_loader() must set extra_cmake_defines to the provided string
        in the Namespace it passes to setup_build_options, so that
        GETDEPS_CMAKE_DEFINES matches the subprocess call."""
        captured_args = []
        custom_defines = '{"MY_VAR":"1"}'

        def fake_setup(args):
            captured_args.append(args)
            mock_opts = MagicMock()
            mock_opts.get_context_generator.return_value = MagicMock()
            return mock_opts

        with (
            patch.object(cgd, "setup_build_options", side_effect=fake_setup),
            patch.object(cgd, "ManifestLoader", return_value=MagicMock()),
        ):
            cgd.create_loader("/tmp/scratch", custom_defines)

        self.assertEqual(len(captured_args), 1)
        args = captured_args[0]
        # Must be byte-identical — no json round-trip
        self.assertEqual(args.extra_cmake_defines, custom_defines)
        # allow_system_packages defaults to False
        self.assertFalse(args.allow_system_packages)
        self.assertFalse(args.shared_libs)

    def test_create_loader_allow_system_packages(self):
        """create_loader() must propagate allow_system_packages=True."""
        captured_args = []

        def fake_setup(args):
            captured_args.append(args)
            mock_opts = MagicMock()
            mock_opts.get_context_generator.return_value = MagicMock()
            return mock_opts

        with (
            patch.object(cgd, "setup_build_options", side_effect=fake_setup),
            patch.object(cgd, "ManifestLoader", return_value=MagicMock()),
        ):
            cgd.create_loader(
                "/tmp/scratch",
                cgd._DEFAULT_CMAKE_DEFINES_JSON,
                allow_system_packages=True,
            )

        self.assertTrue(captured_args[0].allow_system_packages)


# ---------------------------------------------------------------------------
# Raw-string passthrough: the defines string must not be JSON-parsed/re-serialized
# ---------------------------------------------------------------------------


class TestDefinesRawStringPassthrough(unittest.TestCase):
    """The --extra-cmake-defines value must be used verbatim throughout the
    pipeline.  JSON round-tripping would reorder keys and change the byte
    string, invalidating getdeps's hash."""

    def test_non_canonical_json_preserved_in_create_loader(self):
        """A non-canonically-ordered JSON string must survive into create_loader
        unchanged (i.e. it must NOT be parsed and re-dumped)."""
        # Intentionally non-canonical: Z before A, extra spaces
        weird_defines = '{"Z_VAR": "2",  "A_VAR": "1"}'
        captured_args = []

        def fake_setup(args):
            captured_args.append(args)
            mock_opts = MagicMock()
            mock_opts.get_context_generator.return_value = MagicMock()
            return mock_opts

        with (
            patch.object(cgd, "setup_build_options", side_effect=fake_setup),
            patch.object(cgd, "ManifestLoader", return_value=MagicMock()),
        ):
            cgd.create_loader("/tmp/scratch", weird_defines)

        self.assertEqual(captured_args[0].extra_cmake_defines, weird_defines)

    def test_non_canonical_json_preserved_in_build_single_dep(self):
        """A non-canonical JSON string must appear in the subprocess command
        verbatim — not json.loads()'d and re-json.dumps()'d."""
        weird_defines = '{"Z_VAR": "2",  "A_VAR": "1"}'

        mock_opts = MagicMock()
        mock_opts.scratch_dir = "/tmp/scratch"
        mock_loader = MagicMock()
        mock_loader.get_project_install_dir.return_value = "/tmp/inst/gflags"
        mock_loader.get_project_hash.return_value = "abc123"

        with (
            patch.object(cgd.subprocess, "run") as mock_run,
            patch.object(cgd.os.path, "exists", return_value=False),
        ):
            mock_run.return_value = MagicMock(returncode=0)
            cgd.build_single_dep(
                mock_opts, mock_loader, "gflags", weird_defines, "MinSizeRel", None
            )

        cmd = mock_run.call_args[0][0]
        defines_arg = f"--extra-cmake-defines={weird_defines}"
        self.assertIn(defines_arg, cmd)


# ---------------------------------------------------------------------------
# cache_key: build type is included in the key
# ---------------------------------------------------------------------------


class TestCacheKey(unittest.TestCase):
    def test_format_with_build_type(self):
        key = cgd.cache_key("folly", "abc123", "MinSizeRel")
        self.assertEqual(key, "fboss-getdeps-v3-folly-MinSizeRel-abc123")

    def test_includes_project_name(self):
        self.assertIn("gflags", cgd.cache_key("gflags", "xyz", "MinSizeRel"))

    def test_debug_and_minsizerel_keys_differ(self):
        """MinSizeRel and Debug builds must produce different cache keys even
        when the getdeps hash (manifest-based) is identical."""
        key_rel = cgd.cache_key("folly", "same-hash", "MinSizeRel")
        key_dbg = cgd.cache_key("folly", "same-hash", "Debug")
        self.assertNotEqual(key_rel, key_dbg)

    def test_cache_object_url(self):
        url = cgd._cache_object_url(
            "http://cache.example.com", "fboss-getdeps-v3-folly-MinSizeRel-abc"
        )
        self.assertEqual(
            url,
            "http://cache.example.com/fboss-getdeps-v3-folly-MinSizeRel-abc.tar.zst",
        )


# ---------------------------------------------------------------------------
# _maybe_symlink helper
# ---------------------------------------------------------------------------


class TestMaybeSymlink(unittest.TestCase):
    def test_no_dest_is_noop(self):
        with tempfile.TemporaryDirectory() as src:
            cgd._maybe_symlink(src, None)  # should not raise

    def test_same_src_and_dest_is_noop(self):
        with tempfile.TemporaryDirectory() as src:
            cgd._maybe_symlink(src, src)  # should not raise, no symlink created
            self.assertFalse(os.path.islink(src))

    def test_creates_symlink(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            src = os.path.join(tmpdir, "src")
            os.makedirs(src)
            dest = os.path.join(tmpdir, "subdir", "link")
            cgd._maybe_symlink(src, dest)
            self.assertTrue(os.path.islink(dest))
            self.assertEqual(os.readlink(dest), src)

    def test_replaces_existing_symlink(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            src_new = os.path.join(tmpdir, "src_new")
            os.makedirs(src_new)
            dest = os.path.join(tmpdir, "link")
            os.symlink("/old/path", dest)
            cgd._maybe_symlink(src_new, dest)
            self.assertEqual(os.readlink(dest), src_new)


# ---------------------------------------------------------------------------
# check_cache
# ---------------------------------------------------------------------------


class TestCheckCache(unittest.TestCase):
    def test_empty_url_returns_false(self):
        self.assertFalse(cgd.check_cache("", "some-key"))

    def test_http_200_returns_true(self):
        mock_resp = MagicMock()
        mock_resp.status = 200
        with patch.object(cgd.urllib.request, "urlopen", return_value=mock_resp):
            self.assertTrue(cgd.check_cache("http://cache.example.com", "some-key"))

    def test_http_404_returns_false(self):
        with patch.object(
            cgd.urllib.request,
            "urlopen",
            side_effect=urllib.error.HTTPError(None, 404, "Not Found", {}, None),
        ):
            self.assertFalse(cgd.check_cache("http://cache.example.com", "some-key"))

    def test_network_error_returns_false(self):
        with patch.object(
            cgd.urllib.request,
            "urlopen",
            side_effect=urllib.error.URLError("connection refused"),
        ):
            self.assertFalse(cgd.check_cache("http://cache.example.com", "some-key"))

    def test_uses_head_method(self):
        """Must use HEAD (not GET) so we don't download the full tarball."""
        requests_made = []

        def fake_urlopen(req, timeout=None):  # noqa: ARG001
            requests_made.append(req)
            mock_resp = MagicMock()
            mock_resp.status = 200
            return mock_resp

        with patch.object(cgd.urllib.request, "urlopen", side_effect=fake_urlopen):
            cgd.check_cache("http://cache.example.com", "some-key")

        self.assertEqual(len(requests_made), 1)
        self.assertEqual(requests_made[0].method, "HEAD")


# ---------------------------------------------------------------------------
# download_from_cache
# ---------------------------------------------------------------------------


class TestDownloadFromCache(unittest.TestCase):
    def test_empty_url_returns_false(self):
        self.assertFalse(cgd.download_from_cache("", "key", "/tmp/dest"))

    def test_download_failure_returns_false(self):
        with patch.object(
            cgd.urllib.request, "urlretrieve", side_effect=urllib.error.URLError("fail")
        ):
            self.assertFalse(
                cgd.download_from_cache("http://cache.example.com", "key", "/tmp/dest")
            )

    def test_extraction_success(self):
        with tempfile.TemporaryDirectory() as dest:
            tarball_path = os.path.join(tempfile.gettempdir(), "key.tar.zst")

            def fake_retrieve(_url, dst):
                # Create a fake tarball file so unlink works
                open(dst, "wb").close()

            mock_result = MagicMock()
            mock_result.returncode = 0

            with (
                patch.object(
                    cgd.urllib.request, "urlretrieve", side_effect=fake_retrieve
                ),
                patch.object(
                    cgd.subprocess, "run", return_value=mock_result
                ) as mock_run,
                patch.object(cgd.os, "unlink") as mock_unlink,
            ):
                result = cgd.download_from_cache(
                    "http://cache.example.com", "key", dest
                )

            self.assertTrue(result)
            # tarball must be deleted after extraction
            mock_unlink.assert_called_once_with(tarball_path)
            # extraction command must use --strip-components=1 and -C dest
            cmd = mock_run.call_args[0][0]
            self.assertIn("--strip-components=1", cmd)
            self.assertIn(dest, cmd)

    def test_tar_failure_returns_false(self):
        with tempfile.TemporaryDirectory() as dest:

            def fake_retrieve(_url, dst):
                open(dst, "wb").close()

            mock_result = MagicMock()
            mock_result.returncode = 1

            with (
                patch.object(
                    cgd.urllib.request, "urlretrieve", side_effect=fake_retrieve
                ),
                patch.object(cgd.subprocess, "run", return_value=mock_result),
                patch.object(cgd.os, "unlink"),
            ):
                result = cgd.download_from_cache(
                    "http://cache.example.com", "key", dest
                )

            self.assertFalse(result)


# ---------------------------------------------------------------------------
# upload_to_cache
# ---------------------------------------------------------------------------


class TestUploadToCache(unittest.TestCase):
    def test_empty_url_returns_false(self):
        self.assertFalse(cgd.upload_to_cache("", "key", "/some/dir"))

    def test_tar_creation_failure_returns_false(self):
        mock_result = MagicMock()
        mock_result.returncode = 1

        with patch.object(cgd.subprocess, "run", return_value=mock_result):
            result = cgd.upload_to_cache("http://cache.example.com", "key", "/some/dir")

        self.assertFalse(result)

    def test_upload_success(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            src_dir = os.path.join(tmpdir, "mylib-abc123")
            os.makedirs(src_dir)
            tarball_path = os.path.join(tempfile.gettempdir(), "key.tar.zst")
            open(tarball_path, "wb").close()  # fake tarball

            tar_result = MagicMock(returncode=0)
            mock_resp = MagicMock()

            with (
                patch.object(cgd.subprocess, "run", return_value=tar_result),
                patch.object(cgd.os.path, "getsize", return_value=1024 * 1024),
                patch.object(cgd.urllib.request, "urlopen", return_value=mock_resp),
                patch.object(cgd.os.path, "exists", return_value=True),
                patch.object(cgd.os, "unlink") as mock_unlink,
            ):
                result = cgd.upload_to_cache("http://cache.example.com", "key", src_dir)

            self.assertTrue(result)
            # tarball must be cleaned up in finally block
            mock_unlink.assert_called()

    def test_upload_failure_still_returns_true_and_cleans_up(self):
        """Upload failure is non-fatal (just a warning) but tarball must be cleaned."""
        with tempfile.TemporaryDirectory() as tmpdir:
            src_dir = os.path.join(tmpdir, "mylib-abc123")
            os.makedirs(src_dir)

            tar_result = MagicMock(returncode=0)
            tarball_path = os.path.join(tempfile.gettempdir(), "key.tar.zst")
            open(tarball_path, "wb").close()

            with (
                patch.object(cgd.subprocess, "run", return_value=tar_result),
                patch.object(cgd.os.path, "getsize", return_value=1024),
                patch.object(
                    cgd.urllib.request,
                    "urlopen",
                    side_effect=urllib.error.URLError("network error"),
                ),
                patch.object(cgd.os.path, "exists", return_value=True),
                patch.object(cgd.os, "unlink") as mock_unlink,
            ):
                result = cgd.upload_to_cache("http://cache.example.com", "key", src_dir)

            # upload failure warns but still returns True (tarball was created)
            self.assertTrue(result)
            mock_unlink.assert_called()


# ---------------------------------------------------------------------------
# build_single_dep: already-built detection
# ---------------------------------------------------------------------------


class TestBuildSingleDepAlreadyBuilt(unittest.TestCase):
    def test_skips_build_if_hash_matches(self):
        """If .built-by-getdeps marker exists with matching hash, skip build."""
        with tempfile.TemporaryDirectory() as tmpdir:
            inst_dir = os.path.join(tmpdir, "gflags-abc")
            os.makedirs(inst_dir)
            marker = os.path.join(inst_dir, ".built-by-getdeps")
            with open(marker, "w") as f:
                f.write("abc123")

            mock_opts = MagicMock()
            mock_opts.scratch_dir = tmpdir
            mock_loader = MagicMock()
            mock_loader.get_project_install_dir.return_value = inst_dir
            mock_loader.get_project_hash.return_value = "abc123"

            with patch.object(cgd.subprocess, "run") as mock_run:
                result = cgd.build_single_dep(
                    mock_opts,
                    mock_loader,
                    "gflags",
                    cgd._DEFAULT_CMAKE_DEFINES_JSON,
                    "MinSizeRel",
                    None,
                )

            # subprocess.run must NOT be called — dep is already built
            mock_run.assert_not_called()
            self.assertEqual(result, inst_dir)

    def test_rebuilds_if_hash_differs(self):
        """If .built-by-getdeps marker has a different hash, must rebuild."""
        with tempfile.TemporaryDirectory() as tmpdir:
            inst_dir = os.path.join(tmpdir, "gflags-new")
            os.makedirs(inst_dir)
            marker = os.path.join(inst_dir, ".built-by-getdeps")
            with open(marker, "w") as f:
                f.write("old-hash")  # stale hash

            mock_opts = MagicMock()
            mock_opts.scratch_dir = tmpdir
            mock_loader = MagicMock()
            mock_loader.get_project_install_dir.return_value = inst_dir
            mock_loader.get_project_hash.return_value = "new-hash"

            mock_run_result = MagicMock(returncode=0)
            with patch.object(
                cgd.subprocess, "run", return_value=mock_run_result
            ) as mock_run:
                cgd.build_single_dep(
                    mock_opts,
                    mock_loader,
                    "gflags",
                    cgd._DEFAULT_CMAKE_DEFINES_JSON,
                    "MinSizeRel",
                    None,
                )

            mock_run.assert_called_once()


# ---------------------------------------------------------------------------
# _dep_names_in_order: recursive dep ordering
# ---------------------------------------------------------------------------


class TestDepNamesInOrder(unittest.TestCase):
    def _make_manifest(self, name):
        m = MagicMock()
        m.name = name
        return m

    def test_excludes_root_project(self):
        """The root project (fboss) must not appear in the returned list."""
        m_gflags = self._make_manifest("gflags")
        m_folly = self._make_manifest("folly")
        m_fboss = self._make_manifest("fboss")
        mock_loader = MagicMock()
        mock_loader.load_manifest.return_value = m_fboss
        mock_loader.manifests_in_dependency_order.return_value = [
            m_gflags,
            m_folly,
            m_fboss,
        ]

        names = cgd._dep_names_in_order(mock_loader, "fboss")

        self.assertNotIn("fboss", names)
        self.assertIn("gflags", names)
        self.assertIn("folly", names)

    def test_preserves_dependency_order(self):
        """Deps must appear in the same order as manifests_in_dependency_order returns."""
        deps = ["gflags", "glog", "boost", "fmt", "folly"]
        manifests = [self._make_manifest(n) for n in [*deps, "fboss"]]
        mock_loader = MagicMock()
        mock_loader.load_manifest.return_value = manifests[-1]
        mock_loader.manifests_in_dependency_order.return_value = manifests

        names = cgd._dep_names_in_order(mock_loader, "fboss")

        self.assertEqual(names, deps)


# ---------------------------------------------------------------------------
# _build_or_fetch_dep: caching flow
# ---------------------------------------------------------------------------


class TestBuildOrFetchDep(unittest.TestCase):
    """Verify the cache-check → download → build → upload flow."""

    def _make_loader(self, inst_dir, project_hash):
        loader = MagicMock()
        manifest = MagicMock()
        loader.load_manifest.return_value = manifest
        loader.get_project_install_dir.return_value = inst_dir
        loader.get_project_hash.return_value = project_hash
        return loader

    def test_cache_hit_downloads_and_skips_build(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            inst_dir = os.path.join(tmpdir, "folly-abc")
            opts = MagicMock()
            opts.scratch_dir = tmpdir
            loader = self._make_loader(inst_dir, "abc123")

            with (
                patch.object(cgd, "check_cache", return_value=True),
                patch.object(cgd, "download_from_cache", return_value=True) as mock_dl,
                patch.object(cgd, "build_single_dep") as mock_build,
                patch.object(cgd, "upload_to_cache") as mock_upload,
            ):
                # Ensure the marker write doesn't fail
                os.makedirs(inst_dir, exist_ok=True)
                cgd._build_or_fetch_dep(
                    opts,
                    loader,
                    "folly",
                    cgd._DEFAULT_CMAKE_DEFINES_JSON,
                    "MinSizeRel",
                    None,
                    "http://cache",
                    upload=False,
                )

            mock_dl.assert_called_once()
            mock_build.assert_not_called()
            mock_upload.assert_not_called()

    def test_cache_miss_builds_and_uploads_when_flag_set(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            inst_dir = os.path.join(tmpdir, "folly-abc")
            os.makedirs(inst_dir)
            opts = MagicMock()
            opts.scratch_dir = tmpdir
            loader = self._make_loader(inst_dir, "abc123")

            with (
                patch.object(cgd, "check_cache", return_value=False),
                patch.object(cgd, "download_from_cache") as mock_dl,
                patch.object(
                    cgd, "build_single_dep", return_value=inst_dir
                ) as mock_build,
                patch.object(cgd, "upload_to_cache") as mock_upload,
                patch.object(cgd.os.path, "isdir", return_value=True),
            ):
                cgd._build_or_fetch_dep(
                    opts,
                    loader,
                    "folly",
                    cgd._DEFAULT_CMAKE_DEFINES_JSON,
                    "MinSizeRel",
                    None,
                    "http://cache",
                    upload=True,
                )

            mock_dl.assert_not_called()
            mock_build.assert_called_once()
            mock_upload.assert_called_once()

    def test_cache_miss_does_not_upload_when_flag_not_set(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            inst_dir = os.path.join(tmpdir, "folly-abc")
            os.makedirs(inst_dir)
            opts = MagicMock()
            opts.scratch_dir = tmpdir
            loader = self._make_loader(inst_dir, "abc123")

            with (
                patch.object(cgd, "check_cache", return_value=False),
                patch.object(cgd, "build_single_dep", return_value=inst_dir),
                patch.object(cgd, "upload_to_cache") as mock_upload,
                patch.object(cgd.os.path, "isdir", return_value=True),
            ):
                cgd._build_or_fetch_dep(
                    opts,
                    loader,
                    "folly",
                    cgd._DEFAULT_CMAKE_DEFINES_JSON,
                    "MinSizeRel",
                    None,
                    "http://cache",
                    upload=False,
                )

            mock_upload.assert_not_called()

    def test_already_built_locally_skips_cache_and_build(self):
        """If the .built-by-getdeps marker matches, skip cache lookup entirely."""
        with tempfile.TemporaryDirectory() as tmpdir:
            inst_dir = os.path.join(tmpdir, "folly-abc")
            os.makedirs(inst_dir)
            with open(os.path.join(inst_dir, ".built-by-getdeps"), "w") as f:
                f.write("abc123")
            opts = MagicMock()
            loader = self._make_loader(inst_dir, "abc123")

            with (
                patch.object(cgd, "check_cache") as mock_check,
                patch.object(cgd, "build_single_dep") as mock_build,
            ):
                cgd._build_or_fetch_dep(
                    opts,
                    loader,
                    "folly",
                    cgd._DEFAULT_CMAKE_DEFINES_JSON,
                    "MinSizeRel",
                    None,
                    "http://cache",
                    upload=False,
                )

            mock_check.assert_not_called()
            mock_build.assert_not_called()

    def test_system_package_dep_is_skipped(self):
        """System-package deps (e.g. snappy, re2) are OS-provided and have no
        install dir, so getdeps build is a no-op and the upload was silently
        skipped — a permanent cache miss.  They must be skipped outright: no
        cache lookup, no build, no upload."""
        opts = MagicMock()
        loader = self._make_loader("/tmp/inst/snappy-abc", "abc123")
        # MagicMock(spec=...) makes isinstance(m, SystemPackageFetcher) True.
        loader.create_fetcher.return_value = MagicMock(spec=cgd.SystemPackageFetcher)

        with (
            patch.object(cgd, "check_cache") as mock_check,
            patch.object(cgd, "build_single_dep") as mock_build,
            patch.object(cgd, "upload_to_cache") as mock_upload,
        ):
            result = cgd._build_or_fetch_dep(
                opts,
                loader,
                "snappy",
                cgd._DEFAULT_CMAKE_DEFINES_JSON,
                "MinSizeRel",
                None,
                "http://cache",
                upload=True,
            )

        self.assertEqual(result, "")
        mock_check.assert_not_called()
        mock_build.assert_not_called()
        mock_upload.assert_not_called()


# ---------------------------------------------------------------------------
# _precompute_dep_metadata: sequential metadata collection
# ---------------------------------------------------------------------------


class TestPrecomputeDepMetadata(unittest.TestCase):
    """_precompute_dep_metadata classifies deps as _SKIP or _MISS before
    any threads are spawned."""

    def _make_loader(self, deps):
        """deps: list of (name, inst_dir, project_hash, is_system_package)."""
        loader = MagicMock()

        def load_manifest(name):
            m = MagicMock()
            m.name = name
            return m

        loader.load_manifest.side_effect = load_manifest

        def get_install_dir(manifest):
            for n, inst, _, _ in deps:
                if n == manifest.name:
                    return inst
            raise KeyError(manifest.name)

        def get_hash(manifest):
            for n, _, h, _ in deps:
                if n == manifest.name:
                    return h
            raise KeyError(manifest.name)

        def create_fetcher(manifest):
            for n, _, _, sys_pkg in deps:
                if n == manifest.name:
                    if sys_pkg:
                        return MagicMock(spec=cgd.SystemPackageFetcher)
                    return MagicMock()
            raise KeyError(manifest.name)

        loader.get_project_install_dir.side_effect = get_install_dir
        loader.get_project_hash.side_effect = get_hash
        loader.create_fetcher.side_effect = create_fetcher
        return loader

    def test_system_package_dep_gets_skip(self):
        loader = self._make_loader([("snappy", "/inst/snappy", "h1", True)])
        meta = cgd._precompute_dep_metadata(loader, ["snappy"], "MinSizeRel")
        self.assertEqual(len(meta), 1)
        self.assertEqual(meta[0][1], cgd._SKIP)

    def test_already_built_dep_gets_skip(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            inst_dir = os.path.join(tmpdir, "folly-abc")
            os.makedirs(inst_dir)
            with open(os.path.join(inst_dir, ".built-by-getdeps"), "w") as f:
                f.write("abc123")
            loader = self._make_loader([("folly", inst_dir, "abc123", False)])
            meta = cgd._precompute_dep_metadata(loader, ["folly"], "MinSizeRel")
        self.assertEqual(meta[0][1], cgd._SKIP)

    def test_unbuilt_dep_gets_miss(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            inst_dir = os.path.join(tmpdir, "gflags-abc")
            loader = self._make_loader([("gflags", inst_dir, "abc123", False)])
            meta = cgd._precompute_dep_metadata(loader, ["gflags"], "MinSizeRel")
        self.assertEqual(meta[0][1], cgd._MISS)

    def test_marker_hash_mismatch_gives_miss(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            inst_dir = os.path.join(tmpdir, "gflags-abc")
            os.makedirs(inst_dir)
            with open(os.path.join(inst_dir, ".built-by-getdeps"), "w") as f:
                f.write("stale_hash")
            loader = self._make_loader([("gflags", inst_dir, "new_hash", False)])
            meta = cgd._precompute_dep_metadata(loader, ["gflags"], "MinSizeRel")
        self.assertEqual(meta[0][1], cgd._MISS)

    def test_metadata_fields_are_populated(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            inst_dir = os.path.join(tmpdir, "glog-xyz")
            loader = self._make_loader([("glog", inst_dir, "xyz999", False)])
            meta = cgd._precompute_dep_metadata(loader, ["glog"], "Debug")
        name, disp, meta_inst, meta_hash, meta_key = meta[0]
        self.assertEqual(name, "glog")
        self.assertEqual(meta_inst, inst_dir)
        self.assertEqual(meta_hash, "xyz999")
        self.assertIn("glog", meta_key)
        self.assertIn("Debug", meta_key)

    def test_mixed_deps_preserve_order(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            inst_built = os.path.join(tmpdir, "built")
            os.makedirs(inst_built)
            with open(os.path.join(inst_built, ".built-by-getdeps"), "w") as f:
                f.write("h1")
            inst_new = os.path.join(tmpdir, "new")
            deps = [
                ("snappy", "/inst/snappy", "h0", True),  # system pkg → SKIP
                ("gflags", inst_built, "h1", False),  # already built → SKIP
                ("glog", inst_new, "h2", False),  # needs fetch → MISS
            ]
            loader = self._make_loader(deps)
            meta = cgd._precompute_dep_metadata(
                loader, ["snappy", "gflags", "glog"], "MinSizeRel"
            )
        self.assertEqual([m[0] for m in meta], ["snappy", "gflags", "glog"])
        self.assertEqual([m[1] for m in meta], [cgd._SKIP, cgd._SKIP, cgd._MISS])


# ---------------------------------------------------------------------------
# _parallel_check_and_download: parallel S3 check + download phase
# ---------------------------------------------------------------------------


class TestParallelCheckAndDownload(unittest.TestCase):
    """_parallel_check_and_download promotes _MISS→_HIT via HEAD, downloads hits."""

    def _miss(self, name, inst_dir, h="h1"):
        return (name, cgd._MISS, inst_dir, h, cgd.cache_key(name, h, "MinSizeRel"))

    def _skip(self, name):
        return (name, cgd._SKIP, "", "", "")

    def test_no_cache_url_returns_unchanged(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            meta = [self._miss("gflags", os.path.join(tmpdir, "gflags"))]
            result = cgd._parallel_check_and_download(meta, "")
        self.assertEqual(result[0][1], cgd._MISS)

    def test_cache_hit_becomes_hit_and_is_downloaded(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            inst_dir = os.path.join(tmpdir, "gflags")
            os.makedirs(inst_dir)
            meta = [self._miss("gflags", inst_dir)]
            with (
                patch.object(cgd, "check_cache", return_value=True),
                patch.object(cgd, "download_from_cache", return_value=True),
            ):
                result = cgd._parallel_check_and_download(meta, "http://cache")
            self.assertEqual(result[0][1], cgd._HIT)
            # marker must be written while tmpdir still exists
            marker = os.path.join(inst_dir, ".built-by-getdeps")
            self.assertTrue(os.path.exists(marker))

    def test_cache_miss_stays_miss(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            meta = [self._miss("gflags", os.path.join(tmpdir, "gflags"))]
            with patch.object(cgd, "check_cache", return_value=False):
                result = cgd._parallel_check_and_download(meta, "http://cache")
        self.assertEqual(result[0][1], cgd._MISS)

    def test_download_failure_demotes_to_miss(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            inst_dir = os.path.join(tmpdir, "gflags")
            os.makedirs(inst_dir)
            meta = [self._miss("gflags", inst_dir)]
            with (
                patch.object(cgd, "check_cache", return_value=True),
                patch.object(cgd, "download_from_cache", return_value=False),
            ):
                result = cgd._parallel_check_and_download(meta, "http://cache")
        self.assertEqual(result[0][1], cgd._MISS)

    def test_skip_entries_are_untouched(self):
        meta = [self._skip("snappy"), self._skip("re2")]
        with patch.object(cgd, "check_cache", return_value=True) as mock_check:
            result = cgd._parallel_check_and_download(meta, "http://cache")
            mock_check.assert_not_called()
        self.assertEqual(result[0][1], cgd._SKIP)
        self.assertEqual(result[1][1], cgd._SKIP)

    def test_all_deps_downloaded_in_parallel(self):
        """All cache hits must be downloaded regardless of order."""
        call_order = []
        with tempfile.TemporaryDirectory() as tmpdir:
            deps = ["gflags", "glog", "boost", "folly", "fmt"]
            meta = []
            for name in deps:
                d = os.path.join(tmpdir, name)
                os.makedirs(d)
                meta.append(self._miss(name, d))

            def fake_check(_url, _key):
                return True

            def fake_download(_url, key, _dest):
                call_order.append(key)
                return True

            with (
                patch.object(cgd, "check_cache", side_effect=fake_check),
                patch.object(cgd, "download_from_cache", side_effect=fake_download),
            ):
                result = cgd._parallel_check_and_download(meta, "http://cache")

        self.assertTrue(all(r[1] == cgd._HIT for r in result))
        self.assertEqual(len(call_order), len(deps))

    def test_mixed_hits_and_misses(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            hit_dir = os.path.join(tmpdir, "gflags")
            os.makedirs(hit_dir)
            miss_dir = os.path.join(tmpdir, "glog")
            meta = [self._miss("gflags", hit_dir), self._miss("glog", miss_dir)]

            def fake_check(_url, key):
                return "gflags" in key

            with (
                patch.object(cgd, "check_cache", side_effect=fake_check),
                patch.object(cgd, "download_from_cache", return_value=True),
            ):
                result = cgd._parallel_check_and_download(meta, "http://cache")

        self.assertEqual(result[0][1], cgd._HIT)
        self.assertEqual(result[1][1], cgd._MISS)


# ---------------------------------------------------------------------------
# run-getdeps.py: print_info and print_error must go to stderr
# ---------------------------------------------------------------------------


class TestRunGetdepsPrintFunctions(unittest.TestCase):
    """Critical regression test: print_info/print_error must write to stderr.

    Before the fix they wrote to stdout, which corrupted --hash-only output
    read by getdeps_dep.bzl.  The fix redirected them to stderr.
    """

    def setUp(self):
        run_getdeps_path = str(Path(__file__).resolve().parent / "run-getdeps.py")
        spec = importlib.util.spec_from_file_location(
            "run_getdeps_test", run_getdeps_path
        )
        self.rg = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.rg)

    def test_print_info_goes_to_stderr(self):
        captured_out = io.StringIO()
        captured_err = io.StringIO()
        with patch("sys.stdout", captured_out), patch("sys.stderr", captured_err):
            self.rg.print_info("hello info")

        self.assertIn("hello info", captured_err.getvalue())
        self.assertEqual(captured_out.getvalue(), "")

    def test_print_error_goes_to_stderr(self):
        captured_out = io.StringIO()
        captured_err = io.StringIO()
        with patch("sys.stdout", captured_out), patch("sys.stderr", captured_err):
            self.rg.print_error("something failed")

        self.assertIn("something failed", captured_err.getvalue())
        self.assertEqual(captured_out.getvalue(), "")

    def test_print_info_has_ansi_color(self):
        """Info messages should be coloured (yellow) so they stand out in logs."""
        captured_err = io.StringIO()
        with patch("sys.stderr", captured_err):
            self.rg.print_info("check colors")
        # ANSI yellow escape code
        self.assertIn("\033[93m", captured_err.getvalue())

    def test_print_error_has_ansi_color(self):
        """Error messages should be coloured (red)."""
        captured_err = io.StringIO()
        with patch("sys.stderr", captured_err):
            self.rg.print_error("check colors")
        # ANSI red escape code
        self.assertIn("\033[91m", captured_err.getvalue())


if __name__ == "__main__":
    unittest.main(verbosity=2)
