#!/bin/bash

# Script that builds the docker for building FBOSS products

# Defaults
USE_FORCE="no"
BUILD_ISO_IMAGE="no"
ENTER_SHELL="no"
USE_DOCKER_CACHE="yes"
USER=$(whoami)
DOCKER_INSTANCE_NAME=${USER}-fboss-iso-build
DOCKER_IMAGE_NAME=${USER}-fboss-image
BUILD_DOCKER_IMAGE="no"
DELETE_DOCKER_IMAGE="no"
DELETE_DOCKER_CONTAINER="no"
LOG_FILE=$(pwd -P)/build-docker.log

# Change directory full path to correct levels up from the script location as its expected by Dockerfile
SCRIPT_DIR=$(dirname $(readlink -f $0))
IMAGEDIR=$(readlink -f ${SCRIPT_DIR}/..)
CWDSTART=$(readlink -f ${SCRIPT_DIR}/../../..)
cd ${CWDSTART}                      # Switch to "fboss" directory, 2 levels up from this script

print_help() {
    echo "Usage: $0 [options] [--] [options for child scripts]"
    echo ""
    echo "Options:"
    echo ""
    echo "  -b|--build-docker               Build Docker Image to be used for building .ISO image"
    echo "  -C|--skip_docker_cache          Do not use docker cache when building docker image"
    echo "  -d|--delete-docker-container    Stop docker container and the image used for builds"
    echo "  -D|--delete-docker-image        Delete docker container and the image used for building .ISO image"
    echo ""
    echo "  -i|--build-iso-image            Build .ISO image"
    echo ""
    echo "  -e|--enter-shell                Enter shell within the docker container (for debugging)"
    echo ""
    echo "  -l|--log-file <file>            Log file to use (default: ${LOG_FILE})"
    echo "  -h|--help                       Print this help message"
    echo ""
}

# Save all arguments for later use
ORIGINAL_ARGS=("$0" "$@")
# Parse command line arguments
 while [[ "$#" -gt 0 ]]; do
    case "$1" in
        -b|--build-docker)
            BUILD_DOCKER_IMAGE=yes
            shift 1;
            ;;

        -d|--stop-docker-container)
            DELETE_DOCKER_CONTAINER="yes"
            shift 1;
            ;;


        -D|--delete-docker-image)
            DELETE_DOCKER_IMAGE="yes"
            shift 1;
            ;;

        -e|--enter-shell)
            ENTER_SHELL=yes
            shift 1;
            ;;

        -C|--skip_docker_cache)
            USE_DOCKER_CACHE="no"
            shift 1;
            ;;

        -f|--force)
            USE_FORCE="yes"
            shift 1;
            ;;

        -i|--build-iso-image)
            BUILD_ISO_IMAGE="yes"
            shift 1;
            ;;

        -l|--log-file)
            LOG_FILE=$2
            shift 2;
            ;;

        -h|--help)
            print_help
            exit 0
            ;;

        # Stop parsing command line arguments, any thing after the -- is 
        # passed directly to the child process scripts
        --)
            shift 1;
            break
            ;;
        *)  
            echo "Unrecognized command option: '${1}'"
            print_help
            exit 1
            ;;  
    esac
done

CHILD_SCRIPT_ARGS=()
if (( "$#" > 0 )); then
    # Store the remaining arguments (for child process scripts) in an array
    CHILD_SCRIPT_ARGS=("$@") 
fi

# Log everything for posterity ;-)
> ${LOG_FILE}           # Truncate log file
export LOG_FILE

# Source common functions
source ${SCRIPT_DIR}/../lib/functions.sh
dprint "Script launch cmdline: ${ORIGINAL_ARGS[*]}"
dprint " ... logging all output to: ${LOG_FILE}"

# Have we been asked to delete the docker container?
if [ "${DELETE_DOCKER_CONTAINER}" = "yes" ] ; then
    dprint "Stopping and deleting docker containe using image : ${DOCKER_IMAGE_NAME}"
    delete_docker_containers ${DOCKER_IMAGE_NAME}
fi

# Have we been asked to delete the docker image?
if [ "${DELETE_DOCKER_IMAGE}" = "yes" ] ; then
    IMAGEID=$(docker images -q ${DOCKER_IMAGE_NAME})
    if [ -n "${IMAGEID}" ] ; then

        # Stop and delete containers using this image
        dprint "Deleting containers using image: ${DOCKER_IMAGE_NAME}"
        delete_docker_containers ${DOCKER_IMAGE_NAME}

        # Delete the image
        dprint "Deleting image: ${DOCKER_IMAGE_NAME}"
        delete_docker_image     ${DOCKER_IMAGE_NAME}
    else
        dprint "Docker image: ${DOCKER_IMAGE_NAME} does not exist, nothing to delete..."
    fi
fi

# Have we been asked to build the docker image?
RC=0
if [ "${BUILD_DOCKER_IMAGE}" = "yes" ] ; then
    IMAGEID=$(docker images -q ${DOCKER_IMAGE_NAME})
    if [ -n "${IMAGEID}" ] ; then
        dprint "Docker image: ${DOCKER_IMAGE_NAME} already exists, skipping build..."
    else 
        dprint "Building docker image: ${DOCKER_IMAGE_NAME}"
        DOCKER_BUILD_ARGS="  "
        if [ "${USE_DOCKER_CACHE}" = "no" ] ; then
            DOCKER_BUILD_ARGS="--no-cache ${DOCKER_BUILD_ARGS} "
        fi
        # This Dockerfile assumes you are at "nh" directory level
        docker build -f fboss/oss/docker/Dockerfile ${DOCKER_BUILD_ARGS} -t ${DOCKER_IMAGE_NAME} . >> ${LOG_FILE} 2>&1
        handle_error $? "docker build"
    fi
fi

# Main stuff happens here, either we enter the docker in a shell or build ISO or Kernel inside the docker
DOCKER_ARGS=" --privileged --cap-add SYS_ADMIN -v ${IMAGEDIR}:/image_builder -v /dev:/dev --name ${DOCKER_INSTANCE_NAME}"

if [ "${ENTER_SHELL}" = "yes" ] ; then
    dprint "Starting bash in docker container: ${DOCKER_INSTANCE_NAME}"
    docker run -it ${DOCKER_ARGS} ${DOCKER_IMAGE_NAME} /bin/bash

    # housekeeping, remove the container
    dprint "Removing Container after shell exit"
    delete_docker_containers ${DOCKER_IMAGE_NAME}
    handle_error $? "delete_docker_container"
else
    RC0=0; RC1=0;

    if [ "${BUILD_ISO_IMAGE}" = "yes" ] ; then
        dprint "Starting ISO image build, launching in docker: /image_builder/bin/build-image.sh $@"
        docker run -it ${DOCKER_ARGS} ${DOCKER_IMAGE_NAME}     /image_builder/bin/build-image.sh $@ >> ${LOG_FILE} 2>&1
        RC1=$?
        handle_error ${RC1} "docker run - /images/bin/build-iso.sh"
    fi

    # Housekeeping, remove the container(s) if we spawned them
    if [ "${BUILD_ISO_IMAGE}" = "yes" ] ; then
        dprint "Removing container(s)..."
        delete_docker_containers ${DOCKER_IMAGE_NAME}
        handle_error $? "delete_docker_containers (line: ${LINENO})"
    fi

    RC=$((RC0 | RC1))
fi
dprint "$0 execution complete, exit code: ${RC}"
exit ${RC}
