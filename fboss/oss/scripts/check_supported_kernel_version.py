#!/usr/bin/env python3
"""Guard that KernelVersionCheck supports the kernel the distro builds."""

import re
import sys


def main() -> int:
    build_file, check_file = sys.argv[1:]
    with open(build_file) as fh:
        versions = re.findall(
            r'"kernel/scripts/build_kernel\.sh", "([^"]+)"', fh.read()
        )
    if not versions:
        print(f"{build_file}: no build_kernel.sh version found")
        return 1
    with open(check_file) as fh:
        supported = fh.read()
    rc = 0
    for version in versions:
        release = f"{version}-1.fboss.el9.x86_64"
        if f'"{release}"' not in supported:
            print(f"{check_file}: {release} (built by {build_file}) is not supported")
            rc = 1
    return rc


if __name__ == "__main__":
    sys.exit(main())
