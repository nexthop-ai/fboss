#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/nhfboss-common.sh"

# Run inside the build container
set -e
cd /var/FBOSS/fboss

# Build exclusion regex from nh_excluded_tests file
# Each non-empty, non-comment line is treated as a regex pattern
exclude=$(sed 's/#.*//;/^[ 	]*$/d;s/.*/(&)/' "$SCRIPT_DIR/nh_excluded_tests" | tr '\n' '|' | sed 's/|$//')

# Check if --exclude is passed in arguments and combine with our exclusion list
args=()
while [[ $# -gt 0 ]]; do
    user_exclude=""
    case "$1" in
        --exclude=*)
            user_exclude="${1#--exclude=}"
            ;;
        --exclude)
            shift
            user_exclude="$1"
            ;;
        *)
            args+=("$1")
            shift
            continue
            ;;
    esac
    exclude="$exclude|($user_exclude)"
    shift
done

if [[ -n "$exclude" ]]; then
    exclude="--exclude=$exclude"
fi

export BUILD_SAI_FAKE=1
export BUILD_SAI_FAKE_LINK_TEST=1
./fboss/oss/scripts/run-getdeps.py test $common_options --timeout=90 "$exclude" "${args[@]}"
