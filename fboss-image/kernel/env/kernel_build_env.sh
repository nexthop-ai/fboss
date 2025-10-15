#!/bin/bash
# Copyright (c) 2004-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree. An additional grant
# of patent rights can be found in the PATENTS file in the same directory.
# Kernel Build Environment Variables
# Source this file to set up all paths for kernel build scripts

# Determine the kernel build root directory
KERNEL_BUILD_ENV_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Base directories
export KERNEL_BUILD_ROOT="$(cd "$KERNEL_BUILD_ENV_DIR/.." && pwd)"
export PROJECT_ROOT="$(cd "$KERNEL_BUILD_ROOT/../.." && pwd)"

# Kernel build structure
export KERNEL_ENV_DIR="$KERNEL_BUILD_ROOT/env"
export KERNEL_SCRIPTS_DIR="$KERNEL_BUILD_ROOT/scripts"
export KERNEL_SPECS_DIR="$KERNEL_BUILD_ROOT/specs"
export KERNEL_CONFIGS_DIR="$KERNEL_BUILD_ROOT/configs"
export KERNEL_DOCKER_DIR="$KERNEL_BUILD_ROOT/docker"
export KERNEL_DIST_DIR="$KERNEL_BUILD_ROOT/dist"

# Docker configuration
export KERNEL_DOCKER_IMAGE="fboss_builder"

# Spec file and scripts
export KERNEL_SPEC_FILE="$KERNEL_SPECS_DIR/kernel.spec"
export KERNEL_CONFIG_SCRIPT="$KERNEL_SCRIPTS_DIR/prepare_config.sh"
export KERNEL_BUILD_SCRIPT="$KERNEL_SCRIPTS_DIR/build_kernel_in_container.sh"
export KERNEL_BUILD_ALL_SCRIPT="$KERNEL_SCRIPTS_DIR/build_all_kernels.sh"

# FBOSS reference config
export FBOSS_REFERENCE_CONFIG="$KERNEL_CONFIGS_DIR/fboss-reference.config"

# RPM build paths (inside container)
export CONTAINER_WORKSPACE="/workspace"
export CONTAINER_KERNEL_ROOT="$CONTAINER_WORKSPACE/fboss-image/kernel"
export CONTAINER_DIST_DIR="$CONTAINER_KERNEL_ROOT/dist"
export CONTAINER_SPECS_DIR="$CONTAINER_KERNEL_ROOT/specs"
export CONTAINER_SCRIPTS_DIR="$CONTAINER_KERNEL_ROOT/scripts"
export CONTAINER_CONFIGS_DIR="$CONTAINER_KERNEL_ROOT/configs"

# FBOSS supported kernel versions
export FBOSS_KERNEL_VERSIONS=("6.4.3" "6.11.1")

