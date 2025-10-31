#!/bin/bash

# Script that builds a bootable .ISO image using kiwi-ng-3. 

# Change directory full path to correct levels up from the script location so that we can include
# the functions.sh file
SCRIPT_DIR=$(dirname $(readlink -f $0))

# Source common functions
source ${SCRIPT_DIR}/../lib/functions.sh

# Save all arguments for later use
ORIGINAL_ARGS=("$0" "$@")

# Default values
DESCRIPTION_DIR="/image_builder/templates/centos-09.0"
PROFILE="FBOSS"
IMAGE_TYPE="oem"
DELETE_DIR="no"
FBOSS_TARFILE=""
KERNEL_INSTALL_DIR=""
TARGET_DIR=""

if [ -z "${LOG_FILE}" ]; then
    LOG_FILE="$(pwd -P)/build-image.log"
fi

help() {
    echo "Usage: $0 [options]"
    echo ""
    echo "Options:"
    echo "  -d|--description-dir <dir>  kiwi-ng config.xml directory to use (default: ${DESCRIPTION_DIR})"
    echo "  -t|--target-dir <dir>       Target directory, aka output directory (default: output-${IMAGE_TYPE})"
    echo "  -p|--profile <profile>      Build profile to use (default: ${PROFILE})"
    echo "  -i|--image-type <type>      Image type to build (default: ${IMAGE_TYPE})"
    echo ""
    echo "  -f|--fboss-tarfile          Location of compressed FBOSS tar file to add to image"
    echo "  -k|--kernel-install-dir     Location of kernel install directory to add to image"
    echo ""
    echo "  -D|--delete-dir             Delete output directory (if it exists)"
    echo ""
    echo "  -l|--log-file <file>        Log file to use (default: ${LOG_FILE})"
    echo "  -h|--help                   Print this help message"
    echo ""
}

# Once this is finalized, it may be better to use a Dockerfile to build the image
update_docker() {
    dnf install -y \
            epel-release \
            kiwi \
            policycoreutils \
            python3-kiwi \
            dracut-kiwi-live \
            dracut-kiwi-overlay \
            dnf-plugin-versionlock \
            dracut-kiwi-oem-dump \
            kiwi-systemdeps-image-validation \
            syslinux
}

# Parse command line arguments
while [[ "$#" -gt 0 ]]; do
    case "$1" in

        -D|--delete-dir)
            DELETE_DIR="yes"
            shift 1;
            ;;

        -d|--description-dir)
            DESCRIPTION_DIR=$2
            shift 2;
            ;;

        -t|--target-dir)
            TARGET_DIR=$2
            shift 2;
            ;;

        -p|--profile)
            PROFILE=$2
            shift 2;
            ;;

        -i|--image-type)
            IMAGE_TYPE=$2
            shift 2;
            ;;

        -f|--fboss-tarfile)
            FBOSS_TARFILE=$2
            shift 2;
            ;;

        -k|--kernel-install-dir)
            KERNEL_INSTALL_DIR=$2
            shift 2;
            ;;

        -l|--log-file)
            LOG_FILE=$2
            shift 2;
            ;;

        -h|--help)
            help
            exit 0
            ;;
        *)
            echo "Unrecognized command option: '${1}'"
            exit 1
            ;;
    esac
done

# Log everything for posterity ;-)
> ${LOG_FILE}           # Truncate log file
export LOG_FILE

if [ -z "${TARGET_DIR}" -o "${TARGET_DIR}" = "" ]; then
    TARGET_DIR="/image_builder/output-${IMAGE_TYPE}"
fi

dprint "Script launch cmdline: ${ORIGINAL_ARGS[*]}"
dprint " ... logging all output to: ${LOG_FILE}"
dprint " ... output directory: ${TARGET_DIR}"

# Update the docker image, this will be no-op if python3-kiwi is already installed
dprint "Updating docker image..."
update_docker  >> ${LOG_FILE} 2>&1

if [ "${DELETE_DIR}" = "yes" ] ; then
    dprint "Deleting target directory: ${TARGET_DIR}"
    rm -rf ${TARGET_DIR}
fi

# Create the output directory (in case it doesn't exist)
mkdir -p ${TARGET_DIR}
chmod 777 ${TARGET_DIR}

# If you place a tar file in the description directory, it will be automatically extracted and
# overlayed on top of the root file system.  We use this to deploy FBOSS binaries that are generated
# in a different build process.
rm -f ${DESCRIPTION_DIR}/root.tar.gz        # Remove any existing tar file
if [ -n "${FBOSS_TARFILE}" ]; then
    if [ -f "${FBOSS_TARFILE}" ]; then
        dprint "Copying ${FBOSS_TARFILE} to ${DESCRIPTION_DIR}/root.tar.gz ..."
        cp ${FBOSS_TARFILE} ${DESCRIPTION_DIR}/root.tar.gz
    else
        dprint "ERROR: ${FBOSS_TARFILE} does not exist, exiting..."
        exit 1
    fi
fi

# If a kernel install directory is specified, we will copy it over to ${DESCRIPTION_DIR}/root, this 
# will overlay the kernel and modules on top of the root file system.

# Generate the ISO image
dprint "Generating ${IMAGE_TYPE} image, this may take a while..."
kiwi-ng-3 \
    --profile ${PROFILE} \
    --type ${IMAGE_TYPE} \
    --debug system build \
    --description ${DESCRIPTION_DIR} \
    --target-dir ${TARGET_DIR} \
    >> ${LOG_FILE} 2>&1

RC=$?
dprint "Image generation completed with return code ${RC}"
exit ${RC}
