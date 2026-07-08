#!/usr/bin/env python3
# Copyright (c) 2004-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree. An additional grant
# of patent rights can be found in the PATENTS file in the same directory.

"""Read-through / write-back cache for the kernel source tarball.

This is the in-container counterpart to the getdeps ``static_deps`` mirror in
``build/fbcode_builder/getdeps/fetcher.py`` (``ArchiveFetcher``). getdeps already
fronts every third-party download with the internal mirror, but the kernel
tarball is fetched by ``spectool``/``rpmbuild`` *inside the build container*,
where the getdeps package is not mounted -- so we cannot import it and instead
re-use the same, deliberately tiny, convention here:

  * same bucket + endpoint (``vol-shared/fboss/static_deps``);
  * same object key (the upstream URL with non-alnum chars mapped to ``_``), so
    the kernel tarball shares one mirror namespace with everything getdeps caches;
  * read over HTTP, best-effort write-back via ``aws s3 cp --no-sign-request``.

Keep the constants below in sync with ``fetcher.py`` if the mirror ever moves.

Usage:
    cache_source.py fetch --url <upstream_url> --dest SOURCES/linux-6.11.1.tar.xz
    cache_source.py prime --url <upstream_url> --src  SOURCES/linux-6.11.1.tar.xz
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.request

# Mirror of the constants in build/fbcode_builder/getdeps/fetcher.py.
_STATIC_DEPS_HTTP = "http://bucket.internal.nexthop.ai:7480/vol-shared/fboss/static_deps"
_STATIC_DEPS_S3 = "s3://vol-shared/fboss/static_deps"
_STATIC_DEPS_ENDPOINT = "http://bucket.internal.nexthop.ai:7480"


def _object_name(url: str) -> str:
    """Flat, collision-free mirror key derived from the upstream URL.

    Identical to getdeps' ``_static_deps_object_name``: every non-alphanumeric
    character maps to ``_`` so the whole URL becomes one filename. A version
    bump changes the URL and therefore the key, so the mirror re-populates itself.
    """
    return re.sub(r"[^A-Za-z0-9._-]", "_", url)


def fetch(url: str, dest: str) -> int:
    """GET the mirror copy of ``url`` into ``dest``. Return 0 on hit, 1 on miss.

    A 404 (not cached), a network error, or the mirror being unreachable all
    just mean "fetch upstream"; we never retry the mirror.
    """
    mirror = "%s/%s" % (_STATIC_DEPS_HTTP, _object_name(url))
    tmp = dest + ".tmp"
    try:
        print("[cache_source] trying internal mirror: %s" % mirror)
        urllib.request.urlretrieve(mirror, tmp)
    except (urllib.error.URLError, OSError) as e:
        print("[cache_source] mirror miss (%s); will fetch upstream" % e)
        if os.path.exists(tmp):
            os.unlink(tmp)
        return 1
    os.replace(tmp, dest)
    print(
        "[cache_source] fetched %s from mirror (%.1f MB)"
        % (os.path.basename(dest), os.path.getsize(dest) / 1048576)
    )
    return 0


def prime(url: str, src: str) -> int:
    """Best-effort upload of ``src`` to the mirror under ``url``'s key.

    Mirrors getdeps' ``_maybe_upload_to_mirror``: gated on the ``aws`` CLI being
    present, ``--no-sign-request``, and never fails the build. Always returns 0.
    """
    if not os.path.isfile(src):
        print("[cache_source] nothing to prime: %s missing" % src)
        return 0
    if shutil.which("aws") is None:
        print("[cache_source] aws CLI not present; skipping mirror upload")
        return 0
    obj = "%s/%s" % (_STATIC_DEPS_S3, _object_name(url))
    try:
        print("[cache_source] priming mirror: %s -> %s" % (src, obj))
        subprocess.run(
            [
                "aws",
                "--endpoint-url",
                _STATIC_DEPS_ENDPOINT,
                "--no-sign-request",
                "s3",
                "cp",
                src,
                obj,
            ],
            check=True,
            capture_output=True,
            timeout=600,
        )
        print("[cache_source] primed %s" % os.path.basename(src))
    except Exception as e:  # noqa: BLE001 -- best-effort, never fail the build
        print("[cache_source] warning: mirror upload failed (ignored): %s" % e)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="kernel source mirror cache")
    sub = parser.add_subparsers(dest="mode", required=True)

    p_fetch = sub.add_parser("fetch", help="fetch from mirror into --dest")
    p_fetch.add_argument(
        "--url", required=True, help="upstream source URL (mirror key)"
    )
    p_fetch.add_argument("--dest", required=True)

    p_prime = sub.add_parser("prime", help="upload --src to mirror (best-effort)")
    p_prime.add_argument(
        "--url", required=True, help="upstream source URL (mirror key)"
    )
    p_prime.add_argument("--src", required=True)

    args = parser.parse_args()
    if args.mode == "fetch":
        return fetch(args.url, args.dest)
    return prime(args.url, args.src)


if __name__ == "__main__":
    sys.exit(main())
