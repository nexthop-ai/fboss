#!/bin/bash

# Common configuration for nhfboss build scripts
# This file is sourced by nhfboss-build.sh and nhfboss-get-deps.sh

ceildiv() {
    echo $(( ($1 + $2 - 1) / $2 ))
}

# Get the directory where this script is located
COMMON_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

SERVER_RAM_GB=$(free -g | awk '/^Mem:/{print $2}')

# Stop any existing sccache server to ensure clean state
sccache --stop-server > /dev/null 2>&1
# Make sure if OOM that the build gets the short end of the stick.
echo 1000 > /proc/self/oom_score_adj

export SCCACHE_ERROR_LOG="/tmp/sccache.log"
export SCCACHE_LOG=info

# Detect if distributed sccache is available and configure accordingly
SCCACHE_SCHEDULER_HOST=sccache.us-west-1.nexthop.ai
# ping is not available inside the container, and also our scheduler host
# ignores pings.
if timeout 1 bash -c ">/dev/tcp/$SCCACHE_SCHEDULER_HOST/10600" 2>/dev/null; then
    echo "Using sccache scheduler: $SCCACHE_SCHEDULER_HOST"

    export SCCACHE_CONF="$COMMON_SCRIPT_DIR/sccache-dist.toml"
    # With distributed sccache, we can use high parallelism for compilation
    # but linking is local and memory-intensive, so limit it to 2 jobs

    # Running sccache to just send a job somewhere else is cheap. We can do a
    # lot per core, but we still preprocess files locally, and that can take
    # about 1.4G per file.
    COMPILE_JOBS=$(ceildiv $SERVER_RAM_GB 2)

    if sccache --dist-status | grep Disabled; then
        echo Remote sccache not working!
        exit 1
    fi
else
    echo "Only using local sccache cache"
    COMPILE_JOBS=$(ceildiv $SERVER_RAM_GB 8)
fi


# Link parallelism is different from compilation because linking always happens
# on the local machine.
# Empirically, link parallelism of 2 works well on 24GB and 32GB VMs.
LINK_JOBS=$(ceildiv $SERVER_RAM_GB 16)

num_jobs=$((LINK_JOBS > COMPILE_JOBS ? LINK_JOBS : COMPILE_JOBS))

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
# included as extra cmake defines, you need to do rerun nhfboss-get-deps.sh

BUILD_TYPE=${BUILD_TYPE:-MinSizeRel}

# Build common_options for getdeps.py
common_options='--allow-system-packages'
common_options+=' --scratch-path /var/FBOSS/tmp_bld_dir'
common_options+=' --src-dir .'
common_options+=' --extra-cmake-defines {"CMAKE_C_COMPILER_LAUNCHER":"sccache"'
common_options+=',"CMAKE_CXX_COMPILER_LAUNCHER":"sccache"'
common_options+=',"CMAKE_JOB_POOLS":"compile='$COMPILE_JOBS';link='$LINK_JOBS'"'
common_options+=',"CMAKE_JOB_POOL_COMPILE":"compile"'
common_options+=',"CMAKE_JOB_POOL_LINK":"link"}'
common_options+=' fboss'
