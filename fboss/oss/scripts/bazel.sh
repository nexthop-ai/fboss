#!/bin/bash
# Wrapper around bazel that handles build environment setup:
#
#   1. Sources site-specific configuration from fboss-build.env (if present).
#      See fboss-build.env.example for available settings.
#
#   2. Regenerates BUILD.bazel files from BUCK files when inputs change.
#
#   3. Sets up sccache for distributed compilation (idempotent).
#
#   4. Assembles .bazel.d/*.bazelrc fragments into .bazelrc.d (picked up by
#      .bazelrc via try-import). Add your own fragment under .bazel.d/ to
#      customize the build (e.g. remote cache URL, extra flags).
#
# Usage: same as bazel. Either invoke directly:
#   fboss/oss/scripts/bazel.sh build //fboss/...
#
# Or add an alias in your shell config:
#   alias bazel=/var/FBOSS/fboss/fboss/oss/scripts/bazel.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
BAZEL_D="$REPO_ROOT/.bazel.d"
BAZELRC_D="$REPO_ROOT/.bazelrc.d"

# Bridge the BGP++ shipit path for the thrift compiler.
#
# Shipit maps fbcode/neteng/fboss/bgp/public_tld/configerator/structs/neteng/
# to configerator/structs/neteng/ in the OSS repo, but fsdb_model.thrift's
# `include` still references the original internal path under public_tld. The
# thrift genrule resolves includes against the repo root (-I REPO_ROOT), so
# that path has to exist on disk. Create a symlink to bridge the two, mirroring
# the file(CREATE_LINK ...) logic in CMakeLists.txt.
#
# The symlink is deliberately NOT committed to git: committing it makes Bazel's
# //... target globbing follow it into
# configerator/structs/neteng/fboss/thrift/BUILD.bazel and fail (that file
# loads //fboss/build_defs:thrift_library.bzl, an unresolvable label in the
# monorepo workspace). It lives under neteng/ rather than fboss/, so the
# //fboss/... patterns this build targets never traverse it.
BGP_SHIPIT_LINK="$REPO_ROOT/neteng/fboss/bgp/public_tld/configerator/structs/neteng"
if [ ! -L "$BGP_SHIPIT_LINK" ] && [ ! -e "$BGP_SHIPIT_LINK" ]; then
  mkdir -p "$(dirname "$BGP_SHIPIT_LINK")"
  ln -s "$REPO_ROOT/configerator/structs/neteng" "$BGP_SHIPIT_LINK"
fi

# Materialize the hand-written BUILD.bazel files for the BGP++/configerator
# thrift closure that fsdb_model depends on. These packages live under
# configerator/ and neteng/, outside bazelify.py's scan (fboss/, build/,
# common/), so their BUILD.bazel files are not auto-generated.
#
# They are committed as BUILD.bazel.oss and copied into place here rather than
# committed as BUILD.bazel directly: a committed BUILD.bazel would be discovered
# by the Monobuild (nh.git, which has this repo as a submodule) during //...
# expansion, where its `load("//fboss/build_defs:...")` is an unresolvable label
# ('fboss/build_defs' is not a package in that workspace) and aborts the build.
# BUILD.bazel.oss is not a Bazel package marker, so the Monobuild ignores it,
# while the self-contained build here gets a real BUILD.bazel at build time.
# The generated BUILD.bazel files are gitignored.
while IFS= read -r oss_build; do
  [ -f "$oss_build" ] || continue
  dst="${oss_build%.oss}"
  if ! cmp -s "$oss_build" "$dst" 2>/dev/null; then
    cp "$oss_build" "$dst"
  fi
done <<EOF
$REPO_ROOT/configerator/structs/neteng/fboss/bgp/if/BUILD.bazel.oss
$REPO_ROOT/configerator/structs/neteng/bgp_policy/thrift/BUILD.bazel.oss
$REPO_ROOT/configerator/structs/neteng/fboss/bgp/BUILD.bazel.oss
$REPO_ROOT/neteng/fboss/bgp/if/BUILD.bazel.oss
EOF

# Source site-specific configuration if present.
ENV_FILE="$SCRIPT_DIR/fboss-build.env"
if [ -f "$ENV_FILE" ]; then
  # shellcheck source=/dev/null
  source "$ENV_FILE"
fi

# Check that the SAI implementation dependency is configured.  The Bazel build
# currently only supports building with a real SAI implementation.
# build-helper.py adds sai_impl to the fboss manifest when preparing a SAI build.
FBOSS_MANIFEST="$REPO_ROOT/build/fbcode_builder/manifests/fboss"
if [ -f "$FBOSS_MANIFEST" ] && ! grep -q '^sai_impl$' "$FBOSS_MANIFEST"; then
  echo "ERROR: Bazel build requires a SAI implementation (sai_impl not found in fboss manifest)." >&2
  echo "  Run build-helper.py first to configure the SAI implementation:" >&2
  echo "    ./fboss/oss/scripts/build-helper.py <libsai_impl_path> <experiments_path> <output_path> <version>" >&2
  exit 1
fi

# Regenerate Bazel BUILD files if any input (BUCK, .bzl, manifests) changed.
# Uses a content checksum stored in MODULE.bazel to skip when nothing changed.
BAZELIFY_ARGS="--if-needed -r $REPO_ROOT"
if [ -n "${GETDEPS_CACHE_URL:-}" ]; then
  BAZELIFY_ARGS="$BAZELIFY_ARGS --cache-url $GETDEPS_CACHE_URL"
fi
python3 "$SCRIPT_DIR/bazelify.py" $BAZELIFY_ARGS

# Run sccache setup — it writes .bazel.d/sccache.bazelrc.
"$SCRIPT_DIR/bazel-sccache-setup.sh"

# Generate remote-cache.bazelrc if BAZEL_REMOTE_CACHE_URL is configured.
mkdir -p "$BAZEL_D"
REMOTE_RC="$BAZEL_D/remote-cache.bazelrc"
if [ -n "${BAZEL_REMOTE_CACHE_URL:-}" ]; then
  cat >"$REMOTE_RC" <<EOF
# Auto-generated from fboss-build.env -- do not edit
build --remote_cache=$BAZEL_REMOTE_CACHE_URL
# Do not upload from dev machines: without sandboxing, actions can consume
# undeclared inputs that poison the shared cache. CI should override this
# with --remote_upload_local_results=true.
build --remote_upload_local_results=false
build --remote_local_fallback=true
EOF
else
  rm -f "$REMOTE_RC"
fi

# Assemble .bazel.d/*.bazelrc fragments into .bazelrc.d.
# Use a temp file + mv for atomicity (safe under concurrent bazel invocations).
if [ -d "$BAZEL_D" ]; then
  TMP="$(mktemp "$BAZELRC_D.XXXXXX")"
  echo "# Auto-assembled from .bazel.d/*.bazelrc by bazel.sh -- do not edit" >"$TMP"
  for f in "$BAZEL_D"/*.bazelrc; do
    [ -f "$f" ] || continue
    echo "" >>"$TMP"
    echo "# --- $(basename "$f") ---" >>"$TMP"
    cat "$f" >>"$TMP"
  done
  mv "$TMP" "$BAZELRC_D"
fi

# When running tests, append site-local exclusions as negative target patterns.
# Define BAZEL_TEST_EXCLUDE_TARGETS as a bash array in fboss-build.env, e.g.:
#   BAZEL_TEST_EXCLUDE_TARGETS=(
#     "//fboss/fsdb/client/test:fsdb_client_tests"
#   )
if [ "${1:-}" = "test" ] && [ "${#BAZEL_TEST_EXCLUDE_TARGETS[@]}" -gt 0 ]; then
  has_sep=false
  for arg in "$@"; do
    [ "$arg" = "--" ] && {
      has_sep=true
      break
    }
  done
  excludes=()
  $has_sep || excludes+=("--")
  for target in "${BAZEL_TEST_EXCLUDE_TARGETS[@]}"; do
    excludes+=("-$target")
  done
  exec /usr/local/bin/bazel "$@" "${excludes[@]}"
fi
exec /usr/local/bin/bazel "$@"
