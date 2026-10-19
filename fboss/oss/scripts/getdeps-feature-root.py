#!/usr/bin/env python3
"""Run getdeps.py with manifest features resolved from a given root project.

Usage: getdeps-feature-root.py <root-project> <getdeps.py args...>

getdeps resolves [features] from whichever project it is asked to build, so
`getdeps.py build --no-deps glog` sees glog as the only root and drops
features its consumers request (folly-python asks for glog = shared_libs).
That build lands in a different install dir, with different contents, from
the one the full <root-project> graph -- and therefore every dependent and
the cache key -- expects. Resolving from the real root keeps them identical.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(
    0, str(Path(__file__).resolve().parents[3] / "build" / "fbcode_builder")
)

from getdeps.cli import main
from getdeps.load import ManifestLoader


def use_feature_root(root_project: str) -> None:
    resolve_features = ManifestLoader.resolve_features

    def resolve_from_root(self, _roots):
        resolve_features(self, [self.load_manifest(root_project)])

    ManifestLoader.resolve_features = resolve_from_root


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    use_feature_root(sys.argv[1])
    sys.argv = [sys.argv[0], *sys.argv[2:]]
    sys.exit(main())
