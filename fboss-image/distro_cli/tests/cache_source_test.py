#!/usr/bin/env python3
# Copyright (c) 2004-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree. An additional grant
# of patent rights can be found in the PATENTS file in the same directory.

"""Tests for the kernel source read-through/write-back cache helper."""

import http.server
import importlib.util
import socketserver
import sys
import tempfile
import threading
import unittest
from pathlib import Path

# cache_source.py lives under kernel/scripts (mounted into the build container),
# not in the distro_cli package. It is loaded LAZILY (at test runtime, not import
# time) for two reasons:
#   * the CMake test-discovery step imports this module before the build has laid
#     out the test sandbox, so import must not depend on the file being present;
#   * in the CMake sandbox __file__ is a copied path that has no sibling kernel/
#     tree, so we also fall back to the source tree via PYTHONPATH (sys.path).
_cache_source_mod = None


def _cache_source_path() -> Path:
    candidates = [
        Path(__file__).resolve().parents[2] / "kernel" / "scripts" / "cache_source.py"
    ]
    candidates += [
        Path(p) / "kernel" / "scripts" / "cache_source.py" for p in sys.path if p
    ]
    for c in candidates:
        if c.exists():
            return c
    raise FileNotFoundError(f"cache_source.py not found (looked in {candidates})")


def _cs():
    """Load (once) and return the cache_source module."""
    global _cache_source_mod
    if _cache_source_mod is None:
        spec = importlib.util.spec_from_file_location(
            "cache_source", _cache_source_path()
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _cache_source_mod = mod
    return _cache_source_mod


_KERNEL_URL = "https://cdn.kernel.org/pub/linux/kernel/v6.x/linux-6.11.1.tar.xz"


class _Server:
    """Serves a directory over HTTP on an OS-assigned port (GET/HEAD only)."""

    def __init__(self, directory):
        self.directory = str(directory)
        socketserver.TCPServer.allow_reuse_address = True
        self.server = socketserver.TCPServer(
            ("127.0.0.1", 0),
            lambda *a, **k: http.server.SimpleHTTPRequestHandler(
                *a, directory=self.directory, **k
            ),
        )
        self.port = self.server.server_address[1]
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    @property
    def url(self):
        return f"http://127.0.0.1:{self.port}"

    def stop(self):
        self.server.shutdown()
        self.server.server_close()


class TestObjectName(unittest.TestCase):
    def test_matches_getdeps_convention(self):
        # Must be byte-identical to getdeps' _static_deps_object_name so the
        # kernel tarball shares the mirror namespace.
        self.assertEqual(
            _cs()._object_name(_KERNEL_URL),
            "https___cdn.kernel.org_pub_linux_kernel_v6.x_linux-6.11.1.tar.xz",
        )


class TestCacheSourceFetch(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="cache-src-"))
        self.srv = _Server(self.tmp)
        # Point the helper at our test server instead of the real mirror.
        self._orig = _cs()._STATIC_DEPS_HTTP
        _cs()._STATIC_DEPS_HTTP = self.srv.url

    def tearDown(self):
        _cs()._STATIC_DEPS_HTTP = self._orig
        self.srv.stop()

    def test_fetch_hit(self):
        # The mirror object is keyed by the (mangled) upstream URL.
        (self.tmp / _cs()._object_name(_KERNEL_URL)).write_bytes(b"kernel-bytes")
        dest = self.tmp / "out" / "linux-6.11.1.tar.xz"
        dest.parent.mkdir()
        self.assertEqual(_cs().fetch(_KERNEL_URL, str(dest)), 0)
        self.assertEqual(dest.read_bytes(), b"kernel-bytes")

    def test_fetch_miss(self):
        dest = self.tmp / "linux-6.11.1.tar.xz"
        self.assertEqual(_cs().fetch(_KERNEL_URL, str(dest)), 1)
        self.assertFalse(dest.exists())


class TestCacheSourcePrime(unittest.TestCase):
    def test_prime_missing_src_is_noop(self):
        # Missing source must be a no-op success (never fail the build).
        self.assertEqual(_cs().prime(_KERNEL_URL, "/no/such/file"), 0)

    def test_prime_without_aws_is_noop(self):
        # Without the aws CLI the upload is skipped, never raised.
        src = Path(tempfile.mkdtemp(prefix="cache-src-")) / "linux-6.11.1.tar.xz"
        src.write_bytes(b"x")
        cs = _cs()
        orig = cs.shutil.which
        cs.shutil.which = lambda _: None
        try:
            self.assertEqual(cs.prime(_KERNEL_URL, str(src)), 0)
        finally:
            cs.shutil.which = orig


if __name__ == "__main__":
    unittest.main()
