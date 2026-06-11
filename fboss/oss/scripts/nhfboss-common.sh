#!/bin/bash

# Common configuration for nhfboss build scripts
# This file is sourced by nhfboss-build.sh and nhfboss-get-deps.sh

ceildiv() {
  echo $((($1 + $2 - 1) / $2))
}

SERVER_RAM_GB=$(free -g | awk '/^Mem:/{print $2}')

# Calculate number of jobs based on available RAM with varying memory requirements
# Args: first_job_gb [second_job_gb ...] repeating_job_gb
# Each number is the incremental memory requirement for each job. Because
# increasing parallelism does not automatically run all the worst jobs at the
# same time, this is not the same as simply the most demanding job's requirements
# at each step.
# The last memory requirement repeats for all subsequent jobs
# Example: jobs_for_ram 10 5 3
#   Job 1 needs 10GB, job 2 needs 5GB, jobs 3+ each need 3GB
#   With 32GB: job 1 (10GB) + job 2 (5GB) + 5 more jobs (15GB) = 30GB total = 7 jobs
jobs_for_ram() {
  # Leave 2GB for the OS and vscode or whatnot
  local available_ram=$((SERVER_RAM_GB - 2))

  if [ $# -eq 0 ]; then
    echo "Error: jobs_for_ram requires at least one memory requirement argument" >&2
    return 1
  fi

  local job_count=0
  local used_ram=0
  local last_requirement=${*: -1} # Get the last argument (repeating requirement)

  # Process each specified job requirement
  for requirement in "$@"; do
    if [ $((used_ram + requirement)) -le $available_ram ]; then
      used_ram=$((used_ram + requirement))
      job_count=$((job_count + 1))
    else
      echo $job_count
      return 0
    fi
  done

  # Continue adding jobs using the last (repeating) requirement
  while [ $((used_ram + last_requirement)) -le $available_ram ]; do
    used_ram=$((used_ram + last_requirement))
    job_count=$((job_count + 1))
  done

  echo $job_count
}

# Get the directory where this script is located
COMMON_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Stop any existing sccache server to ensure clean state
sccache --stop-server >/dev/null 2>&1 || true
# Make sure if OOM that the build gets the short end of the stick.
echo 1000 >/proc/self/oom_score_adj

export SCCACHE_ERROR_LOG="/tmp/sccache.log"
export SCCACHE_LOG=info

# Detect if distributed sccache is available and configure accordingly
SCCACHE_SCHEDULER_HOST=sccache.us-west-1.nexthop.ai
SCCACHE_SCHEDULER_PORT=10600
SCCACHE_DIST_CONFIG="$COMMON_SCRIPT_DIR/sccache-dist.toml"
# Check if the scheduler is actually responding to API requests, not just accepting TCP connections
# Extract the auth token from the config file
SCCACHE_AUTH_TOKEN=$(grep '^token = ' "$SCCACHE_DIST_CONFIG" | sed 's/^token = "\(.*\)"$/\1/')
if [[ -z $SCCACHE_AUTH_TOKEN ]]; then
  echo "ERROR: Failed to extract auth token from $SCCACHE_DIST_CONFIG"
  echo 'Expected format: token = "..."'
  exit 1
fi
curl_output=$(curl -s -o /dev/null -w '%{http_code}' -m 2 -H "Authorization: Bearer $SCCACHE_AUTH_TOKEN" "http://$SCCACHE_SCHEDULER_HOST:$SCCACHE_SCHEDULER_PORT/api/v1/scheduler/status" 2>&1)
curl_exit_code=$?
http_code="${curl_output##*$'\n'}"

if [[ $http_code != "200" ]]; then
  echo "ERROR: sccache scheduler at $SCCACHE_SCHEDULER_HOST:$SCCACHE_SCHEDULER_PORT is not responding!"
  if [[ $http_code == "000" ]] || [[ $curl_exit_code -ne 0 ]]; then
    echo "Connection failed (curl exit code: $curl_exit_code)"
    if [[ $curl_output != "000" ]]; then
      echo "Error details: $curl_output"
    fi
  else
    echo "HTTP status code: $http_code (expected 200)"
  fi
  echo "Please check the scheduler status or contact the infrastructure team."
  exit 1
fi

echo "Using sccache scheduler: $SCCACHE_SCHEDULER_HOST"

export SCCACHE_CONF="$COMMON_SCRIPT_DIR/sccache-dist.toml"
# With distributed sccache, we can use high parallelism for compilation
# but linking is local and memory-intensive, so limit it to 2 jobs

# Running sccache to just send a job somewhere else is cheap. We can do a
# lot per core, but we still preprocess files locally, and that can eat into
# our RAM, which is important because we need a lot of it for linking.
nproc_jobs=$(($(nproc) * 20))
ram_jobs=$((SERVER_RAM_GB * 5))
COMPILE_JOBS=$((nproc_jobs < ram_jobs ? nproc_jobs : ram_jobs))

if [[ ${BUILD_TYPE:-} == "Debug" ]]; then
  # PathValidator.cpp takes at least 32 minutes to build in debug mode
  # Increase timeout to 45 minutes
  export SCCACHE_DIST_REQUEST_TIMEOUT=2700
  # Need to increase the idle timeout also, otherwise the local sccache
  # server will exit because only *starting* a compile job counts as
  # activity.
  export SCCACHE_IDLE_TIMEOUT=2700
fi

if sccache --dist-status | grep Disabled; then
  echo Remote sccache not working!
  exit 1
fi

# Stop the server because we haven't configured S3 yet.
sccache --stop-server >/dev/null 2>&1 || true
if [ $COMPILE_JOBS -eq 0 ]; then
  echo "Not enough memory to compile"
  exit 1
fi

# Link parallelism is different from compilation because linking always happens
# on the local machine.
if [[ ${BUILD_TYPE:-} == "Debug" ]]; then
  # Even 1 job is too much for 32GB
  # 2 link jobs works with 64GB of RAM, with 7.5GB available at the low point
  # 1 link job on 64GB VM peaks at 48GB of RAM
  # 2 link jobs on 64GB VM peak at 56GB of RAM
  LINK_JOBS=$(jobs_for_ram 48 8)
else
  # 2 works well on 24GB and 32GB VMs.
  LINK_JOBS=$(jobs_for_ram 11)
fi
if [ $LINK_JOBS -eq 0 ]; then
  echo "Not enough memory to link"
  exit 1
fi
echo "Using $COMPILE_JOBS compile jobs and $LINK_JOBS link jobs"

export num_jobs=$((LINK_JOBS > COMPILE_JOBS ? LINK_JOBS : COMPILE_JOBS))

ENDPOINT_HOST=bucket.internal.nexthop.ai
ENDPOINT_PORT=7480
if timeout 1 bash -c ">/dev/tcp/$ENDPOINT_HOST/$ENDPOINT_PORT" 2>/dev/null; then
  export SCCACHE_BUCKET=sccache
  export SCCACHE_ENDPOINT=$ENDPOINT_HOST:$ENDPOINT_PORT
  export SCCACHE_S3_KEY_PREFIX=fboss
  export SCCACHE_REGION=auto
  export AWS_ACCESS_KEY_ID=R74SNIY3OLH45CN19OWC
  export AWS_SECRET_ACCESS_KEY=4rsA7lOZU0JbX81SZSTQ3nDs2ZslKlcvPdIgdOMP
  echo "Using sccache bucket: $ENDPOINT_HOST:$ENDPOINT_PORT/$SCCACHE_BUCKET/$SCCACHE_S3_KEY_PREFIX"
fi

# Note: Because COMPILE_JOBS and LINK_JOBS depend on SERVER_RAM_GB, and they're
# included as extra cmake defines, you need to rerun nhfboss-get-deps.sh when
# server RAM changes.

BUILD_TYPE=${BUILD_TYPE:-MinSizeRel}

build_dir=${build_dir:-/var/FBOSS/tmp_bld_dir}

# Build common_options for getdeps.py
common_options='--allow-system-packages'
common_options+=' --scratch-path '$build_dir
common_options+=' --src-dir .'
common_options+=' --extra-cmake-defines {"CMAKE_C_COMPILER_LAUNCHER":"sccache"'
common_options+=',"CMAKE_CXX_COMPILER_LAUNCHER":"sccache"'
common_options+=',"CMAKE_JOB_POOLS":"compile='$COMPILE_JOBS';link='$LINK_JOBS'"'
common_options+=',"CMAKE_JOB_POOL_COMPILE":"compile"'
common_options+=',"CMAKE_JOB_POOL_LINK":"link"'
common_options+=',"RANGE_V3_TESTS":"OFF"'
common_options+=',"RANGE_V3_PERF":"OFF"'
common_options+=',"CMAKE_EXPORT_COMPILE_COMMANDS":"ON"'
if [ -n "${BUILD_CFBOSS:-}" ]; then
  common_options+=',"BUILD_CFBOSS":"ON"'
fi
common_options+='}'
common_options+=' --num-jobs '$num_jobs
common_options+=' fboss'
