#!/bin/bash
# Usage: generated_files_identical.sh <actual> <expected> <fix_hint...>
# Bazel tokenizes args, so the hint arrives as $3 onwards.

if ! diff -u "$2" "$1"; then
  echo "" >&2
  echo "${*:3}" >&2
  exit 1
fi
