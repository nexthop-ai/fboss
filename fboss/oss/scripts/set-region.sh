#!/bin/bash
# Select the build region: point region.env, region.repo and region.proxy.env
# at that region's files under regions/. The launchers load the first two and
# the genrules export the third on the host; there is no default. The proxy
# file is <region>.proxy, not .env, so the region list below stays honest.
# By hand: bazel run //fboss:set_region -- <region>
# From the fboss genrules: set-region.sh --from-env, which selects the region
# in NH_CLOUD_PROVIDER (passed with --action_env), else the one selected
# earlier, and is a no-op with neither.
set -euo pipefail
cd "$(dirname "$(readlink -f "$0")")"
region=${1:-}
if [[ $region == --from-env ]]; then
  region=${NH_CLOUD_PROVIDER:-}
  if [[ -z $region ]]; then
    # No provider from CI: keep the region selected earlier, re-linking any
    # file that selection predates.
    target=$(readlink region.env 2>/dev/null) || exit 0
    region=${target#regions/}
    region=${region%.env}
  fi
fi
if [[ ! -f regions/$region.env || ! -f regions/$region.proxy ]]; then
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
link "regions/$region.proxy" region.proxy.env
echo "build region set to $region"
