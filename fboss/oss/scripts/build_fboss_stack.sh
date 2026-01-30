#!/usr/bin/env bash
#
# Build script for FBOSS forwarding and platform stacks
# This script builds the specified stack binaries inside a container.
#
# Prerequisites (handled by build_entrypoint.py):
#   - SAI SDK extracted to /opt/sdk (from /deps/sai tarball)
#   - Kernel RPMs installed (from /deps/kernel tarball, optional)
#
# This script:
#   - Parses the requested stack type (forwarding or platform)
#   - For forwarding, enables SAI/SDK handling via need_sai=1
#   - Detects SAI location at /opt/sdk (when need_sai=1)
#   - Configures SAI environment variables (when need_sai=1)
#   - Builds FBOSS dependencies
#   - Builds the appropriate FBOSS CMake target
#   - Packages artifacts into tarballs
#
set -euxo pipefail

if [ "$#" -lt 1 ]; then
  echo "Usage: $0 forwarding|platform" >&2
  exit 1
fi

# Global variables (populated by helper functions)
build_dir=""
stack_label=""

# Source helper functions
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/fboss-stack-helper.sh"

# Determine number of parallel jobs for building
# Returns a reasonable number based on available CPU cores and memory
determine_jobs() {
  local nproc_count
  local ram_gb
  local ram_jobs
  local jobs

  nproc_count=$(nproc)
  ram_gb=$(free -g | awk '/^Mem:/{print $2}')

  # Reserve 2GB for OS, use remaining for build jobs
  # Assume each job needs ~4GB for compilation and linking
  ram_jobs=$(((ram_gb - 2) / 4))

  # Use the minimum of CPU cores and RAM-based jobs, but at least 1
  jobs=$nproc_count
  if [ $ram_jobs -lt $jobs ]; then
    jobs=$ram_jobs
  fi

  if [ $jobs -lt 1 ]; then
    jobs=1
  fi

  echo $jobs
}

# Setup FBOSS build environment
# Sets up output directory, build type, number of jobs, and common options
# Requires: build_dir (set by setup_build_env)
setup_fboss_build_env() {
  BUILD_TYPE="${BUILD_TYPE:-MinSizeRel}"

  num_jobs=$(determine_jobs)
  echo "Using $num_jobs parallel jobs"

  # Build common options for getdeps.py
  common_options='--allow-system-packages'
  common_options+=' --scratch-path '$build_dir
  common_options+=' --src-dir .'
  common_options+=' fboss'
}

stack_type="$1"

# Setup build environment
setup_build_env "$stack_type"

# Navigate to FBOSS source root
cd /var/FBOSS/fboss

# Setup FBOSS build environment
setup_fboss_build_env

echo "Building FBOSS ${stack_label} stack"

# Setup SAI environment
setup_sai_env "$stack_type"

# Save manifest snapshot before modifying manifests
save_manifest_snapshot

# Setup build dependencies
setup_build_deps

# Run build and package
run_build

# Restore manifest snapshot after build
restore_manifest_snapshot
