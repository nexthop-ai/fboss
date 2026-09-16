#!/bin/bash
# Reports descriptor asic_config.yaml copies with no entry in fboss/descriptor_asic_configs.bzl.
# Each argument is the path of an uncovered copy.

status=0

for path in "$@"; do
  status=1
  echo "$path: no entry in fboss/descriptor_asic_configs.bzl." >&2
  echo "  Add it to _DESCRIPTOR_COPIES so the copy is diffed against its generated source." >&2
done

exit $status
