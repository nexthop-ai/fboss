#!/bin/bash
# Minimal build script for testing the build infrastructure
# This script creates an empty artifact file for testing purposes
set -e

# Create the output artifact
touch "$1"
