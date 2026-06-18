#!/bin/bash
# Download and initialize the prebuilt SAI implementation if needed.
#
# The SAI tarball is cached under /var/extras/sai/<version>/ (the host's
# $HOME/work/caches directory mounted into the build container at /var/extras).
# On a fresh GARM runner /var/extras/sai/<version>/ starts empty and this
# script downloads it from the internal S3 bucket.
#
# Usage:
#   SAI_VERSION=1.16.1 bash fboss/oss/scripts/ensure-sai.sh
#
# Set SAI_VERSION in the environment to override the default version.
# To force a re-download without waiting for an S3 ETag change, delete the
# ".etag" file in the same folder as the SAI tarball, e.g.
#   rm /var/extras/sai/1.16.1/.etag

set -euo pipefail

sai_version="${SAI_VERSION:-1.16.1}"
s3_url="http://bucket.internal.nexthop.ai:7480/vol-shared/fboss/sai/libsai_impl-${sai_version}-fboss.tar.gz"
cache_dir="/var/extras/sai/${sai_version}"
tarball="${cache_dir}/libsai_impl.tar.gz"
etag_file="${cache_dir}/.etag"
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "${script_dir}/../../.." && pwd)"
sai_impl_manifest="${repo_root}/build/fbcode_builder/manifests/sai_impl"
fboss_manifest="${repo_root}/build/fbcode_builder/manifests/fboss"

# Quick HEAD request to detect upstream tarball updates (5 s timeout;
# left empty and skipped when the S3 bucket is unreachable or returns no ETag).
s3_etag=$(curl --silent --max-time 5 --head "$s3_url" 2>/dev/null |
  grep -i '^etag:' | tr -d '\r' | awk '{print $2}') || true

# Download if the tarball is absent or the S3 ETag has changed.
need_download=false
if [ ! -f "$tarball" ]; then
  need_download=true
elif [ -n "$s3_etag" ] &&
  { [ ! -f "$etag_file" ] || [ "$s3_etag" != "$(cat "$etag_file")" ]; }; then
  echo "SAI ${sai_version}: updated tarball detected on S3, refreshing..." >&2
  need_download=true
fi

# Initialize if the download is fresh or the sai_impl manifest is absent/stale.
need_init=false
if $need_download ||
  [ ! -f "$sai_impl_manifest" ] ||
  ! grep -q '^sai_impl$' "$fboss_manifest" 2>/dev/null; then
  need_init=true
fi

$need_download || $need_init || exit 0

if $need_download; then
  echo "Downloading SAI ${sai_version}..." >&2
  mkdir -p "$cache_dir"
  tmp_tarball="${tarball}.tmp"
  tmp_headers="${cache_dir}/.headers.tmp"
  if ! curl --fail --dump-header "$tmp_headers" -o "$tmp_tarball" "$s3_url"; then
    echo "ERROR: failed to download ${s3_url}" >&2
    rm -f "$tmp_tarball" "$tmp_headers"
    exit 1
  fi
  mv -f "$tmp_tarball" "$tarball"
  # Use ETag from the GET response headers — consistent with the file we just wrote.
  download_etag=$(grep -i '^etag:' "$tmp_headers" | tr -d '\r' | awk '{print $2}')
  rm -f "$tmp_headers"
  [ -n "$download_etag" ] && printf '%s\n' "$download_etag" >"$etag_file"
fi

if $need_init; then
  echo "Initializing SAI ${sai_version}..." >&2
  csum=$(sha256sum "$tarball" | awk '{print $1}')
  # Write the sai_impl manifest pointing directly to S3.  getdeps downloads
  # from there when the install dir is absent, bypassing the old HTTP server
  # approach that build-helper.py used to manage.
  cat >"$sai_impl_manifest" <<EOF
[manifest]
name = sai_impl

[download]
url = ${s3_url}
sha256 = ${csum}
[build]
builder = nop

[install.files]
lib = lib
include = include
EOF
  # Ensure sai_impl is listed as a dependency in the fboss manifest.
  if [ -f "$fboss_manifest" ] && ! grep -q '^sai_impl$' "$fboss_manifest"; then
    sed -i '/^\[dependencies\]$/a sai_impl' "$fboss_manifest"
  fi
fi
