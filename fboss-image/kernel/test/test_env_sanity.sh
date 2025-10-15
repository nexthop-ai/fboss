#!/bin/bash
# Copyright (c) 2004-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree. An additional grant
# of patent rights can be found in the PATENTS file in the same directory.

# Test script for kernel build environment validation

set -e

# Get script directory and source environment
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../env/kernel_build_env.sh"

# Minimal helper
die() { echo "FAIL: $*" >&2; exit 1; }

# Validation function
validate_kernel_build_env() {
    local missing_paths=()
    # Check critical directories
    [[ ! -d "$KERNEL_BUILD_ROOT" ]] && missing_paths+=("KERNEL_BUILD_ROOT: $KERNEL_BUILD_ROOT")
    [[ ! -d "$KERNEL_SCRIPTS_DIR" ]] && missing_paths+=("KERNEL_SCRIPTS_DIR: $KERNEL_SCRIPTS_DIR")
    [[ ! -d "$KERNEL_SPECS_DIR" ]] && missing_paths+=("KERNEL_SPECS_DIR: $KERNEL_SPECS_DIR")
    # Check critical files
    [[ ! -f "$KERNEL_SPEC_FILE" ]] && missing_paths+=("KERNEL_SPEC_FILE: $KERNEL_SPEC_FILE")
    [[ ! -f "$KERNEL_CONFIG_SCRIPT" ]] && missing_paths+=("KERNEL_CONFIG_SCRIPT: $KERNEL_CONFIG_SCRIPT")

    if [[ ${#missing_paths[@]} -gt 0 ]]; then
        echo "ERROR: Missing kernel build environment paths:" >&2
        printf "  %s\n" "${missing_paths[@]}" >&2
        return 1
    fi
    return 0
}

# Test environment validation
if ! validate_kernel_build_env; then
  die "Environment validation failed"
fi

# Test that all required variables are set
required_vars=(
    "KERNEL_BUILD_ROOT"
    "PROJECT_ROOT"
    "KERNEL_SCRIPTS_DIR"
    "KERNEL_SPECS_DIR"
    "KERNEL_CONFIGS_DIR"
    "KERNEL_DIST_DIR"
    "FBOSS_KERNEL_VERSIONS"
)

for var in "${required_vars[@]}"; do
  [[ -n "${!var:-}" ]] || die "Required var not set: $var"
done

# Test that kernel versions array is populated
if [[ ${#FBOSS_KERNEL_VERSIONS[@]} -eq 0 ]]; then die "FBOSS_KERNEL_VERSIONS array is empty"; fi

# Ensure required config files exist
[[ -f "$KERNEL_CONFIGS_DIR/fboss-reference.config" ]] || die "Missing file: $KERNEL_CONFIGS_DIR/fboss-reference.config"
[[ -f "$KERNEL_CONFIGS_DIR/fboss-local-overrides.yaml" ]] || die "Missing file: $KERNEL_CONFIGS_DIR/fboss-local-overrides.yaml"

# Validate YAML syntax of fboss-local-overrides.yaml
if command -v python3 >/dev/null 2>&1; then
  python3 -c "import yaml; yaml.safe_load(open('$KERNEL_CONFIGS_DIR/fboss-local-overrides.yaml'))" 2>/dev/null \
    || die "YAML syntax validation failed: $KERNEL_CONFIGS_DIR/fboss-local-overrides.yaml"
fi

# Syntax check key scripts
for f in \
  "$KERNEL_SCRIPTS_DIR/build_kernel_in_container.sh" \
  "$KERNEL_SCRIPTS_DIR/build_kernel.sh" \
  "$KERNEL_SCRIPTS_DIR/prepare_config.sh" \
  "$KERNEL_SCRIPTS_DIR/build_all_kernels.sh"
do
  if [[ -f "$f" ]]; then
    bash -n "$f" || die "Syntax check failed: $f"
  fi
done

# rpmspec macro behavior sanity (skip if rpmspec not available)
if command -v rpmspec >/dev/null 2>&1; then
  if rpmspec -P "$KERNEL_SPECS_DIR/kernel.spec" >/dev/null 2>&1; then
    die "kernel.spec should error without kernel_version"
  fi
  rpmspec -P "$KERNEL_SPECS_DIR/kernel.spec" --define 'kernel_version 6.11.1' >/dev/null 2>&1 \
    || die "rpmspec -P failed with kernel_version defined"
fi

# Host tools required by host-side scripts
command -v docker >/dev/null 2>&1 || die "docker not found in PATH (required for containerized builds)"

# Ensure build orchestrator is executable
[[ -x "$KERNEL_BUILD_SCRIPT" ]] || die "KERNEL_BUILD_SCRIPT not executable: $KERNEL_BUILD_SCRIPT"

# Spec sanity: ensure config sources are embedded as Source1/Source2
grep -q '^Source1:' "$KERNEL_SPECS_DIR/kernel.spec" || die "kernel.spec missing Source1: fboss-reference.config"
grep -q '^Source2:' "$KERNEL_SPECS_DIR/kernel.spec" || die "kernel.spec missing Source2: fboss-local-overrides.yaml"
grep -q '%{SOURCE1}' "$KERNEL_SPECS_DIR/kernel.spec" || die "kernel.spec missing %{SOURCE1} usage in prepare step"
grep -q '%{SOURCE2}' "$KERNEL_SPECS_DIR/kernel.spec" || die "kernel.spec missing %{SOURCE2} usage in prepare step"

echo "All environment tests passed."

