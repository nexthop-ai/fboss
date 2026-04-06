#!/bin/bash
# Build the bgp_pp (bgp++) RPM package.
#
# This script runs INSIDE the distro build container. It expects the bgp++
# binary tarball to already be present at rpmbuild/SOURCES/bgp_pp-1.0.tar.gz
# (placed by Bazel via the @bgp_pp_tarball repo rule before the container starts).

set -euo pipefail

TARBALL="rpmbuild/SOURCES/bgp_pp-1.0.tar.gz"

if [[ ! -f $TARBALL ]]; then
  echo "ERROR: bgp++ tarball not found at $TARBALL"
  echo "The tarball should be placed by Bazel (@bgp_pp_tarball) before the build."
  exit 1
fi

dnf builddep -y --spec rpmbuild/SPECS/bgp_pp.spec

rm -rf rpmbuild/RPMS/*
mkdir -p rpmbuild/{RPMS,SRPMS,BUILD,BUILDROOT}

rpmbuild -bb --define "_topdir $(pwd)/rpmbuild" rpmbuild/SPECS/bgp_pp.spec

cp rpmbuild/RPMS/x86_64/bgp-pp-*.x86_64.rpm /output/
