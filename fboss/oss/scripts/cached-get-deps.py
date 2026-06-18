#!/usr/bin/env python3
"""Build or fetch a single third-party dependency (or all deps recursively) with caching.

This script wraps Meta's getdeps build system to build one dependency at a
time, with a per-dependency caching layer backed by an HTTP cache server
(e.g., bazel-remote or a radosgw bucket).

Usage:
    # Build gflags, using cache if available:
    cached-get-deps.py --project gflags

    # Build all deps for fboss recursively, using cache:
    cached-get-deps.py --project fboss --recursive \\
        --cache-url http://bucket.internal:7480/getdeps-cache \\
        --extra-cmake-defines '{"CMAKE_JOB_POOLS":"compile=40;link=4",...}' \\
        --build-type MinSizeRel --allow-system-packages --upload

    # Just compute and print the hash (for debugging):
    cached-get-deps.py --project gflags --hash-only
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

# Import getdeps modules without modifying them.
FBCODE_BUILDER_DIR = str(
    Path(__file__).resolve().parents[3] / "build" / "fbcode_builder"
)
sys.path.insert(0, FBCODE_BUILDER_DIR)

from getdeps.buildopts import setup_build_options  # noqa: E402
from getdeps.fetcher import SystemPackageFetcher  # noqa: E402
from getdeps.load import ManifestLoader  # noqa: E402

# Import detect_toolchain and setup_clang_environment from the sibling
# run-getdeps.py so we set up the same clang flags/rpath/LD_LIBRARY_PATH
# that a normal getdeps build uses.
_run_getdeps_path = str(Path(__file__).resolve().parent / "run-getdeps.py")
_spec = importlib.util.spec_from_file_location("run_getdeps", _run_getdeps_path)
_run_getdeps_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_run_getdeps_mod)
detect_toolchain = _run_getdeps_mod.detect_toolchain
setup_clang_environment = _run_getdeps_mod.setup_clang_environment

# Default CMake defines used by the Bazel repo-rule path (no job pools, stable
# keys for cross-machine caching).  The cmake path passes its own defines via
# --extra-cmake-defines from nhfboss-common.sh.
_DEFAULT_CMAKE_DEFINES: dict[str, str] = {
    "RANGE_V3_TESTS": "OFF",
    "RANGE_V3_PERF": "OFF",
    # glog's manifest sets BUILD_SHARED_LIBS=ON; override it so all deps
    # produce static archives that Bazel can consume without LD_LIBRARY_PATH.
    "BUILD_SHARED_LIBS": "OFF",
    # Match nhfboss-get-deps.sh (MinSizeRel = -Os -DNDEBUG, no debug info).
    "CMAKE_BUILD_TYPE": "MinSizeRel",
    # Prevent double-wrapping sccache in the Bazel build.
    "CMAKE_CXX_COMPILER_LAUNCHER": "",
    "CMAKE_C_COMPILER_LAUNCHER": "",
}
_DEFAULT_CMAKE_DEFINES_JSON: str = json.dumps(_DEFAULT_CMAKE_DEFINES)


def create_loader(
    scratch_path: str,
    extra_cmake_defines: str,
    allow_system_packages: bool = False,
) -> tuple[object, ManifestLoader]:
    """Set up BuildOptions and ManifestLoader, reusing getdeps internals."""
    args = argparse.Namespace(
        scratch_path=scratch_path,
        install_prefix=None,
        host_type=None,
        facebook_internal=False,
        vcvars_path=None,
        allow_system_packages=allow_system_packages,
        lfs_path=None,
        shared_libs=False,
        # Must match --extra-cmake-defines passed to the getdeps subprocess so
        # that GETDEPS_CMAKE_DEFINES is identical in both hash computations.
        extra_cmake_defines=extra_cmake_defines,
    )
    opts = setup_build_options(args)
    ctx_gen = opts.get_context_generator()
    loader = ManifestLoader(opts, ctx_gen)
    return opts, loader


def _maybe_symlink(src_dir: str, dest: str | None) -> None:
    """If dest is set and differs from src_dir, create/replace a symlink."""
    if not dest or dest == src_dir:
        return
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    if os.path.lexists(dest):
        os.remove(dest)
    os.symlink(src_dir, dest)


# Bump when cached tarballs contain baked-in paths that become stale, e.g.
# after fixing allow_system_packages consistency so cmake configs reference
# the correct dep install dirs instead of the old mismatched paths.
_CACHE_VERSION = "v2"


def cache_key(project_name: str, project_hash: str, build_type: str) -> str:
    """Compute a cache key for a dependency tarball.

    build_type is included because getdeps does NOT hash --build-type into the
    project hash, so MinSizeRel and Debug builds would otherwise share a key.
    _CACHE_VERSION is bumped when baked-in paths inside cached tarballs become
    stale, forcing a one-time cold rebuild.
    """
    return f"fboss-getdeps-{_CACHE_VERSION}-{project_name}-{build_type}-{project_hash}"


def _cache_object_url(cache_url: str, key: str) -> str:
    """Compute the URL for a cached tarball."""
    return f"{cache_url}/{key}.tar.zst"


def check_cache(cache_url: str, key: str) -> bool:
    """Check if a cached tarball exists in the remote cache."""
    if not cache_url:
        return False
    url = _cache_object_url(cache_url, key)
    try:
        req = urllib.request.Request(url, method="HEAD")
        resp = urllib.request.urlopen(req, timeout=10)
        return resp.status == 200
    except (urllib.error.URLError, urllib.error.HTTPError):
        return False


def download_from_cache(cache_url: str, key: str, dest_dir: str) -> bool:
    """Download and extract a cached tarball."""
    if not cache_url:
        return False
    url = _cache_object_url(cache_url, key)
    tarball = os.path.join(tempfile.gettempdir(), f"{key}.tar.zst")
    try:
        urllib.request.urlretrieve(url, tarball)
    except (urllib.error.URLError, urllib.error.HTTPError):
        return False

    # Extract into dest_dir
    os.makedirs(dest_dir, exist_ok=True)
    result = subprocess.run(
        ["tar", "--zstd", "-xf", tarball, "-C", dest_dir, "--strip-components=1"],
        check=False,
        capture_output=True,
    )
    os.unlink(tarball)
    return result.returncode == 0


def upload_to_cache(cache_url: str, key: str, src_dir: str) -> bool:
    """Create a tarball and upload to the remote cache."""
    if not cache_url:
        return False
    tarball = os.path.join(tempfile.gettempdir(), f"{key}.tar.zst")

    # Create tarball
    result = subprocess.run(
        [
            "tar",
            "--zstd",
            "-cf",
            tarball,
            "-C",
            os.path.dirname(src_dir),
            os.path.basename(src_dir),
        ],
        check=False,
        capture_output=True,
    )
    if result.returncode != 0:
        return False

    tarball_size = os.path.getsize(tarball)
    url = _cache_object_url(cache_url, key)
    try:
        with open(tarball, "rb") as f:
            req = urllib.request.Request(url, data=f, method="PUT")
            req.add_header("Content-Type", "application/octet-stream")
            req.add_header("Content-Length", str(tarball_size))
            urllib.request.urlopen(req, timeout=600)
        print(f"  Uploaded to cache ({tarball_size / 1048576:.1f} MB)")
    except (urllib.error.URLError, urllib.error.HTTPError) as e:
        print(f"  Warning: cache upload failed: {e}")
    finally:
        if os.path.exists(tarball):
            os.unlink(tarball)
    return True


def build_single_dep(
    opts,
    loader: ManifestLoader,
    project_name: str,
    extra_cmake_defines: str,
    build_type: str,
    num_jobs: int | None,
) -> str:
    """Build a single dependency using getdeps, assuming deps are already installed.

    Returns the install directory path.
    """
    manifest = loader.load_manifest(project_name)
    inst_dir = loader.get_project_install_dir(manifest)
    project_hash = loader.get_project_hash(manifest)

    # Check if already built with matching hash
    built_marker = os.path.join(inst_dir, ".built-by-getdeps")
    if os.path.exists(built_marker):
        with open(built_marker) as f:
            existing_hash = f.read().strip()
        if existing_hash == project_hash:
            print("  Already built (hash matches)")
            return inst_dir

    # Use getdeps.py build --no-deps to build just this project.
    repo_root = str(Path(FBCODE_BUILDER_DIR).parent.parent)
    cmd = [
        sys.executable,
        os.path.join(FBCODE_BUILDER_DIR, "getdeps.py"),
        "build",
        "--no-deps",
        "--no-tests",
        "--scratch-path",
        opts.scratch_dir,
        f"--extra-cmake-defines={extra_cmake_defines}",
        "--build-type",
        build_type,
    ]
    if num_jobs is not None:
        cmd += ["--num-jobs", str(num_jobs)]
    if getattr(opts, "allow_system_packages", False):
        cmd.append("--allow-system-packages")
    cmd.append(project_name)

    print(f"  Building {project_name}...")
    result = subprocess.run(cmd, check=False, cwd=repo_root)
    if result.returncode != 0:
        print(
            f"  ERROR: build failed with exit code {result.returncode}", file=sys.stderr
        )
        sys.exit(1)

    return inst_dir


def _build_or_fetch_dep(
    opts,
    loader: ManifestLoader,
    project_name: str,
    extra_cmake_defines: str,
    build_type: str,
    num_jobs: int | None,
    cache_url: str,
    upload: bool,
) -> str:
    """Fetch from cache or build a single dep; upload on cache miss. Returns install dir."""
    manifest = loader.load_manifest(project_name)

    # System-package deps (manifests with an [rpms]/[debs] section, resolved
    # under --allow-system-packages) are provided by the OS — installed via dnf
    # in the builder image.  getdeps neither builds nor installs them, so
    # `getdeps build --no-deps <proj>` is a no-op that leaves no install dir.
    # That made every such dep a permanent "Cache MISS — building" with a
    # silently-skipped upload (os.path.isdir(result_dir) is False).  There is
    # nothing to cache, so skip them outright — mirroring bazelify.py's
    # is_system handling.  The final `run-getdeps build --only-deps` pass
    # (also --allow-system-packages) likewise relies on the OS copies.
    if isinstance(loader.create_fetcher(manifest), SystemPackageFetcher):
        print(f"[{project_name}] system package (OS-provided) — skipping")
        return ""

    inst_dir = loader.get_project_install_dir(manifest)
    project_hash = loader.get_project_hash(manifest)
    key = cache_key(project_name, project_hash, build_type)

    print(f"[{project_name}] hash={project_hash[:30]}... key={key[:55]}...")

    # Already built locally with matching hash — skip everything.
    built_marker = os.path.join(inst_dir, ".built-by-getdeps")
    if os.path.exists(built_marker):
        with open(built_marker) as f:
            if f.read().strip() == project_hash:
                print("  Already built (hash matches)")
                return inst_dir

    # Try downloading from cache.
    if cache_url and check_cache(cache_url, key):
        print("  Cache HIT — downloading...")
        if download_from_cache(cache_url, key, inst_dir):
            with open(os.path.join(inst_dir, ".built-by-getdeps"), "w") as f:
                f.write(project_hash)
            print(f"  Installed to {inst_dir}")
            return inst_dir
        print("  Download/extract failed, falling back to build...")

    # Cache miss (or download failure) — build from source.
    print("  Cache MISS — building...")
    result_dir = build_single_dep(
        opts, loader, project_name, extra_cmake_defines, build_type, num_jobs
    )

    # Upload to cache (CI sets --upload / GETDEPS_CACHE_UPLOAD=1; dev machines skip).
    if upload and cache_url and os.path.isdir(result_dir):
        upload_to_cache(cache_url, key, result_dir)

    return result_dir


def _dep_names_in_order(loader: ManifestLoader, root_project: str) -> list[str]:
    """Return transitive dep names in build order, excluding the root project itself."""
    root_manifest = loader.load_manifest(root_project)
    ordered = loader.manifests_in_dependency_order(root_manifest)
    return [m.name for m in ordered if m.name != root_project]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build or fetch a cached third-party dependency"
    )
    parser.add_argument(
        "--project", required=True, help="Dependency name (e.g., gflags, folly, fboss)"
    )
    parser.add_argument(
        "--recursive",
        action="store_true",
        help="Build all transitive deps of --project in dependency order "
        "(the project itself is excluded). Used with --project fboss to "
        "cache all third-party deps for the cmake build.",
    )
    parser.add_argument(
        "--scratch-path", default="/var/FBOSS/tmp_bld_dir", help="Scratch directory"
    )
    parser.add_argument(
        "--cache-url",
        default="",
        help="HTTP cache server URL for dep tarballs (empty = no caching)",
    )
    parser.add_argument(
        "--extra-cmake-defines",
        default="",
        dest="extra_cmake_defines",
        help="Raw JSON cmake defines string passed verbatim to getdeps "
        "(must be byte-identical to the string used by the final fboss build "
        "so dep install-dir hashes match). Defaults to the Bazel-path defines.",
    )
    parser.add_argument(
        "--build-type",
        default="MinSizeRel",
        help="CMake build type (MinSizeRel, Debug, RelWithDebInfo). "
        "Included in the cache key to prevent type collisions.",
    )
    parser.add_argument(
        "--allow-system-packages",
        action="store_true",
        help="Pass --allow-system-packages to getdeps (must match the real build invocation).",
    )
    parser.add_argument(
        "--num-jobs",
        type=int,
        default=None,
        help="Number of parallel jobs for getdeps builds.",
    )
    parser.add_argument(
        "--upload",
        action="store_true",
        default=os.environ.get("GETDEPS_CACHE_UPLOAD", "") == "1",
        help="Upload built deps to the cache (default: off; set GETDEPS_CACHE_UPLOAD=1 or pass flag). "
        "Only CI should upload to avoid polluting the shared cache.",
    )
    parser.add_argument(
        "--install-dir", help="Override install directory (for Bazel repo rule)"
    )
    parser.add_argument(
        "--hash-only", action="store_true", help="Just print the project hash and exit"
    )
    args = parser.parse_args()

    # Use the caller-supplied defines verbatim, or fall back to Bazel defaults.
    extra_cmake_defines = args.extra_cmake_defines or _DEFAULT_CMAKE_DEFINES_JSON

    repo_root = str(Path(FBCODE_BUILDER_DIR).parent.parent)

    # Set up clang environment before any getdeps operations.
    toolchain_info = detect_toolchain()
    if toolchain_info and toolchain_info.get("type") == "clang":
        setup_clang_environment(toolchain_info, repo_root=repo_root)

    opts, loader = create_loader(
        args.scratch_path,
        extra_cmake_defines,
        allow_system_packages=args.allow_system_packages,
    )

    if args.hash_only:
        manifest = loader.load_manifest(args.project)
        print(loader.get_project_hash(manifest))
        return 0

    if args.recursive:
        # Build all transitive deps of --project in dependency order.
        dep_names = _dep_names_in_order(loader, args.project)
        print(
            f"Building {len(dep_names)} deps for {args.project} in dependency order..."
        )
        for dep_name in dep_names:
            _build_or_fetch_dep(
                opts,
                loader,
                dep_name,
                extra_cmake_defines,
                args.build_type,
                args.num_jobs,
                args.cache_url,
                args.upload,
            )
        print("All deps done.")
        return 0

    # Single-project mode (original Bazel repo-rule path).
    manifest = loader.load_manifest(args.project)
    project_hash = loader.get_project_hash(manifest)
    inst_dir = loader.get_project_install_dir(manifest)
    key = cache_key(args.project, project_hash, args.build_type)

    print(f"[{args.project}] hash={project_hash[:30]}... cache_key={key[:50]}...")

    # Try downloading from cache
    if args.cache_url and check_cache(args.cache_url, key):
        print("  Cache HIT — downloading...")
        if download_from_cache(args.cache_url, key, inst_dir):
            # Write marker so getdeps recognizes it
            with open(os.path.join(inst_dir, ".built-by-getdeps"), "w") as f:
                f.write(project_hash)
            print(f"  Installed to {inst_dir}")
            _maybe_symlink(inst_dir, args.install_dir)
            return 0

    # Cache miss — build
    print("  Cache MISS — building...")
    result_dir = build_single_dep(
        opts, loader, args.project, extra_cmake_defines, args.build_type, args.num_jobs
    )

    # Upload to cache
    if args.upload and args.cache_url and os.path.isdir(result_dir):
        upload_to_cache(args.cache_url, key, result_dir)

    _maybe_symlink(result_dir, args.install_dir)
    print(f"  Installed to {result_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
