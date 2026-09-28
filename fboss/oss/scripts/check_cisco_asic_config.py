#!/usr/bin/env python3
"""Guard the wedge800c Cisco device_property that upstream config syncs keep emptying."""

import json
import sys


def main() -> int:
    rc = 0
    for path in sys.argv[1:]:
        with open(path) as fh:
            common = json.load(fh)["platform"]["chip"]["asicConfig"]["common"]
        if not json.loads(common["jsonConfig"])["devices"][0].get("device_property"):
            print(f"{path}: devices[0].device_property is empty")
            rc = 1
    if rc:
        print("Take upstream's file and restore device_property from previous version.")
    return rc


if __name__ == "__main__":
    sys.exit(main())
