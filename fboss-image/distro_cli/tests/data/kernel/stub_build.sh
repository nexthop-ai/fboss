#!/bin/bash
# Stub kernel build script for testing
# Creates a minimal kernel artifact tarball for testing purposes
set -e

OUTPUT_DIR="${1:-/output}"

echo "Stub kernel build - creating test artifact"

# Create a minimal kernel RPM structure
mkdir -p "$OUTPUT_DIR"
cd "$OUTPUT_DIR"

# Create a dummy kernel RPM file
echo "dummy kernel rpm" >kernel-test.rpm

# Create the tarball
tar -czf kernel-test.rpms.tar.gz kernel-test.rpm

# Clean up
rm kernel-test.rpm

echo "Stub kernel artifact created: $OUTPUT_DIR/kernel-test.rpms.tar.gz"
