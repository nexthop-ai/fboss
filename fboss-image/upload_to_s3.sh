#!/bin/bash

# Script to upload FBOSS.bin image to Amazon S3 using nexis commands
# This script automates the process of renaming, initializing a build, uploading, and committing

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ -z $1 ]]; then
  echo "Usage: $0 <path/to/FBOSS.bin>" >&2
  exit 1
fi
FBOSS_BIN="$1"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo_error() {
  echo -e "${RED}ERROR: $1${NC}" >&2
}

echo_success() {
  echo -e "${GREEN}$1${NC}"
}

echo_warning() {
  echo -e "${YELLOW}WARNING: $1${NC}"
}

echo_info() {
  echo "$1"
}

# Check if the .bin file exists
if [[ ! -f $FBOSS_BIN ]]; then
  echo_error "FBOSS bin not found at $FBOSS_BIN"
  exit 1
fi

# Check AWS credentials
echo_info "Checking AWS credentials..."
aws sts get-caller-identity &>/dev/null
AWS_EXIT_CODE=$?
if [[ $AWS_EXIT_CODE -ne 0 ]]; then
  echo_error "AWS credentials are not configured or are invalid"
  echo_info ""
  echo_info "Please follow the steps outlined at:"
  echo_info "  http://ind/51-AWS-creds"
  echo_info ""
  echo_info "The nexis-buildrunner upload command requires AWS credentials to be set up."
  exit 1
fi

echo_success "AWS credentials verified"

# Generate new filename with date
DATE_SUFFIX=$(date +"%Y%m%d")
NEW_FILENAME="FBOSS-OS-SAI13.3-rel-${DATE_SUFFIX}.bin"
NEW_FILEPATH="${SCRIPT_DIR}/${NEW_FILENAME}"

# Rename the file
echo_info "Renaming ${FBOSS_BIN} to ${NEW_FILENAME}..."
cp "$FBOSS_BIN" "$NEW_FILEPATH"
echo_success "File renamed successfully"

# Initialize nexis build
echo_info "Initializing nexis build..."
BUILD_OUTPUT=$(nexis-buildrunner init --repo nh/private-fboss --branch main --platform broadcom 2>&1)
NEXIS_EXIT_CODE=$?
echo "$BUILD_OUTPUT"

# Extract build ID - it's just a number on the last line
BUILD_ID=$(echo "$BUILD_OUTPUT" | grep -oP '^\d+$' | tail -1)

if [[ -z $BUILD_ID ]]; then
  echo_error "Failed to extract build-id from nexis-buildrunner init output"
  echo_info "Output was:"
  echo "$BUILD_OUTPUT"
  echo_info "Exit code was: $NEXIS_EXIT_CODE"
  exit 1
fi

echo_success "Build initialized with ID: $BUILD_ID"

# Upload image to S3
echo_info "Uploading image to S3..."
nexis-buildrunner upload --image "$NEW_FILEPATH" --build-id "$BUILD_ID"
UPLOAD_EXIT_CODE=$?
if [[ $UPLOAD_EXIT_CODE -eq 0 ]]; then
  echo_success "Image uploaded successfully"
else
  echo_error "Failed to upload image to S3 (exit code: $UPLOAD_EXIT_CODE)"
  exit 1
fi

# Commit the build
echo_info "Marking build as successful..."
nexis-buildrunner commit --build-id "$BUILD_ID"
COMMIT_EXIT_CODE=$?
if [[ $COMMIT_EXIT_CODE -eq 0 ]]; then
  echo_success "Build marked as successful"
else
  echo_error "Failed to commit build (exit code: $COMMIT_EXIT_CODE)"
  exit 1
fi

# Display success message and warnings
echo ""
echo_success "=========================================="
echo_success "FBOSS image uploaded successfully!"
echo_success "=========================================="
echo_info "Build ID: $BUILD_ID"
echo_info "Image: $NEW_FILENAME"
echo ""

# Warning about latest stable mechanism
echo_warning "=========================================="
echo_warning "IMPORTANT NOTE"
echo_warning "=========================================="
echo_warning "The mechanism to mark FBOSS images as 'latest stable' is currently broken."
echo_warning ""
echo_warning "For more information and updates, see:"
echo_warning "  https://nexthopai.slack.com/archives/C0992P1QENM/p1769033536422479"
echo_warning ""
echo_info "To see all currently available FBOSS images, run:"
echo_info "  nexis show --repo nh/private-fboss --status success"
echo ""

# Clean up - optionally remove the renamed file
read -p "Do you want to remove the renamed file ${NEW_FILENAME}? [y/N] " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
  rm "$NEW_FILEPATH"
  echo_info "Renamed file removed"
else
  echo_info "Renamed file kept at: $NEW_FILEPATH"
fi
