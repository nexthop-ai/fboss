#!/bin/bash
# Select the build region: point region.env and region.repo at that region's
# files under regions/. The launchers load those two paths; there is no default.
# By hand: bazel run //fboss:set_region -- <region>
# From the fboss genrules: set-region.sh --from-env, which selects the region
# in NH_CLOUD_PROVIDER (passed with --action_env) and is a no-op without it.
set -euo pipefail
cd "$(dirname "$(readlink -f "$0")")"
region=${1:-}
if [[ $region == --from-env ]]; then
  [[ -n ${NH_CLOUD_PROVIDER:-} ]] || exit 0
  region=$NH_CLOUD_PROVIDER
fi
if [[ ! -f regions/$region.env ]]; then
  regions=(regions/*.env)
  regions=("${regions[@]##*/}")
  echo "usage: bazel run //fboss:set_region -- <region>, one of: ${regions[*]%.env}" >&2
  exit 1
fi
# Genrules run this concurrently: replace each link atomically so a container
# starting at the same moment never sees it missing.
link() {
  [[ $(readlink "$2" 2>/dev/null) == "$1" ]] && return
  ln -s "$1" "$2.tmp.$$" && mv -Tf "$2.tmp.$$" "$2"
}
link "regions/$region.env" region.env
link "regions/local_mirror.$region.repo" region.repo
echo "build region set to $region"
