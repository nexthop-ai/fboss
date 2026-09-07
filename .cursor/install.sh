#!/usr/bin/env bash
# Cloud Agent install script for FBOSS.
#
# Sets up the reliably-runnable developer flows for this repository:
#   * Python tooling for the OSS test runner and lint hooks
#     (pytest suite under fboss/oss/scripts/run_scripts, ruff, pre-commit).
#   * Node/yarn dependencies for the Docusaurus documentation site (docs/).
#
# Note: The full FBOSS C++ agent daemon is built out-of-band via
# fboss/oss/scripts/docker-build.py / getdeps (see BUILD.md). That build pulls
# and compiles a very large dependency tree (folly, fbthrift, wangle, SAI, ...)
# and is intentionally NOT run here.
#
# This script is idempotent and safe to re-run.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

echo "==> Installing Python dev dependencies (user site)"
python3 -m pip install --user --upgrade \
  -r requirements-dev.txt \
  'pytest>=8,<9' \
  'parameterized>=0.9,<1' \
  ruff

echo "==> Installing docs (Docusaurus) dependencies"
if command -v yarn >/dev/null 2>&1; then
  # Use the committed lockfile when present for reproducible installs; fall
  # back to a plain install (which resolves/creates a lockfile) otherwise.
  if [[ -f docs/yarn.lock ]]; then
    (cd docs && yarn install --frozen-lockfile)
  else
    (cd docs && yarn install)
  fi
else
  echo "WARN: yarn not found on PATH; skipping docs dependency install" >&2
fi

echo "==> Installing pre-commit git hook"
# Install the git hook so commits are linted. Downloading the hook
# environments (clang-format, shellcheck, shfmt, ruff, ...) needs network and
# is best-effort so a transient failure does not fail environment setup.
python3 -m pre_commit install || echo "WARN: 'pre-commit install' failed" >&2
python3 -m pre_commit install-hooks ||
  echo "WARN: 'pre-commit install-hooks' failed (hooks will install on first run)" >&2

echo "==> Install complete"
echo "    Run tests: python3 -m pytest fboss/oss/scripts/run_scripts/fboss_test_runner/unittests/"
echo "    Lint:      python3 -m ruff check fboss/"
echo "    Docs:      cd docs && yarn start"
