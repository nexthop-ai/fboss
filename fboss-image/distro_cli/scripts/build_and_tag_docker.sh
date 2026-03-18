#!/bin/bash
# Build and tag the fboss_builder Docker image with checksum

set -e

python3 -c "
import sys
sys.path.insert(0, 'fboss/fboss-image')
from distro_cli.lib.docker.image import build_fboss_builder_image
build_fboss_builder_image()
"
