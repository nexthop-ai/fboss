#!/usr/bin/env bash
#
# Kiwi <repository customize="..."> hook.
#
# Kiwi can only emit a single source URL per <repository>, but at build time we
# want to prefer Nexthop's local CentOS/EPEL mirror, and fall back to the
# upstream mirror network automatically when the local mirror is down or
# internally inconsistent.
#
# dnf/librepo merges a repo's baseurl entries and its metalink-derived mirrors
# into a single ordered pool with the baseurl tried first. So for a repo whose
# baseurl is the local mirror, appending the matching upstream metalink here
# yields local-first, upstream-fallback resolution -- exactly local_mirror.repo.
#
# Kiwi invokes this as: bash --norc mirror-fallback.sh <path-to-generated.repo>

set -euo pipefail

repo_file="$1"

# Kiwi writes the repository alias as the [section] header on the first line.
IFS= read -r first_line <"$repo_file"
alias="${first_line#[}"
alias="${alias%]}"

case "$alias" in
CentOS9-ExtrasCommon)
  metalink='https://mirrors.centos.org/metalink?repo=centos-extras-sig-extras-common-9-stream&arch=x86_64&protocol=https,http'
  ;;
CentOS9-BaseOS)
  metalink='https://mirrors.centos.org/metalink?repo=centos-baseos-9-stream&arch=x86_64&protocol=https,http'
  ;;
CentOS9-AppStream)
  metalink='https://mirrors.centos.org/metalink?repo=centos-appstream-9-stream&arch=x86_64&protocol=https,http'
  ;;
CentOS9-CRB)
  metalink='https://mirrors.centos.org/metalink?repo=centos-crb-9-stream&arch=x86_64&protocol=https,http'
  ;;
EPEL)
  metalink='https://mirrors.fedoraproject.org/metalink?repo=epel-9&arch=x86_64'
  ;;
KiwiTools)
  metalink='https://download.opensuse.org/repositories/Virtualization:/Appliances:/Builder/CentOS_10/repodata/repomd.xml.metalink'
  ;;
*)
  # No known upstream fallback for this repo; leave it untouched.
  exit 0
  ;;
esac

# Append the upstream fallback and the same tuning knobs local_mirror.repo uses.
# These lines land under the section header Kiwi already wrote.
cat >>"$repo_file" <<EOF
metalink=$metalink
metadata_expire=6h
countme=1
cost=500
timeout=15
EOF
