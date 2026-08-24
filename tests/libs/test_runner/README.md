# FBOSS Hardware Test Runner

`runner.py` defines per-test-type runner classes (`SaiTestRunner`,
`BspTestRunner`, etc.) consumed by pytest fixtures in
`fboss/tests/conftest.py`. Each runner deploys the test binaries it needs
onto a DUT and then drives `run_test.py` over SSH.

This README documents the deploy/cache behavior so you don't have to
reverse-engineer it from the code.

## Env-var contract

The orchestrator (`nhtests-run` via `TestInstanceFboss._resolve_artifact_urls`)
resolves *what* to use and forwards it; the runner *consumes* it and decides
whether it has what it needs. Per the runner's `STACK` (`forwarding` or
`platform`) it gets **either** a Nexis tarball URL **or** a locally-built CMake
build dir:

| Env var | Source | Used for |
| --- | --- | --- |
| `FBOSS_FORWARDING_TARBALL_URL` / `FBOSS_PLATFORM_TARBALL_URL` | orchestrator: Nexis CloudStack URL | the runner fetches + extracts the tarball |
| `FBOSS_FORWARDING_LOCAL_DIR` / `FBOSS_PLATFORM_LOCAL_DIR` | orchestrator: a locally-built CMake `build/fboss` dir | the runner packs the slice straight from these binaries + the repo's `share/` configs (no staging copy) |
| `FBOSS_BUILD_ID` | `--test-build-id` (Nexis) | cache/marker namespace for the Nexis path. (The local path derives its namespace from a fingerprint of the runner's uploaded sources — see [Local namespace](#local-namespace).) |
| `DUT`, `DUTUSERNAME`, `DUTPASSWORD`, `HWSKU`, `TESTFILE` | testbed inventory | SSH/SCP to the DUT + drive `run_test.py` |
| `TESTFILTER` | `--test-filter` (nhtests-run) | gtest-style expression for `run_test.py`  |


The orchestrator resolves *which* source to use — explicit `--test-build-id` →
local CMake build → build_id stamped on the running DUT — and forwards **only**
what it found (possibly nothing). It never errors on "couldn't resolve"; the
runner raises loudly at deploy time if neither a `*_LOCAL_DIR` nor a
`*_TARBALL_URL` is set for its `STACK`. The local path (`FBOSS_*_LOCAL_DIR`) is
preferred when present.

## Per-runner manifest

Each runner declares two things:

- **`STACK`** — `forwarding` or `platform`; selects the Nexis artifact name and
  the local CMake build subdir.
- **`BINARIES`** — the test binary(ies) this runner runs. This is the only
  per-runner knob, and it mirrors the upstream on-DUT test runner
  (`fboss/oss/scripts/run_scripts/fboss_test_runner/runners/*.py`), the source of
  truth for binary names. `test_runner_deploy.py` cross-checks every `BINARIES`
  entry against that package and fails loudly on drift.

`REQUIRED_PATHS` — the full set deployed to the DUT — is composed as
`(*BINARIES, *_STACK_SHARE[STACK])`:

- **Binaries are sliced per runner** — they're large (~1 GB each), so a runner
  ships only the one(s) it runs.
- **`share/` configs are shipped wholesale per stack** via `_STACK_SHARE`. The
  forwarding tree (`hw_test_configs`, every
  `*_known_bad_tests` / `*_unsupported_tests`, `production_features`,
  `hw_benchmark_tests`, …) is ~19 MB — cheaper to ship in full than to maintain a
  per-runner subset that can silently miss a file. Platform tests read no
  `share/` configs, so `_STACK_SHARE[platform]` is empty.
  `share/hw_bench_configs` is the one exception: only `BenchmarkTestRunner` reads
  it, so it appends the dir to its own `REQUIRED_PATHS` instead.

`run_test.py` and `setup_fboss_env` are **not** shipped — every runner relies on
the production image already on the DUT (`/opt/fboss/bin/`).

| Runner | Stack | `BINARIES` | Extra |
| --- | --- | --- | --- |
| `SaiTestRunner` | forwarding | `bin/sai_test-sai_impl` | — |
| `SaiAgentTestRunner` | forwarding | `bin/sai_agent_hw_test-sai_impl`, `bin/multi_switch_agent_hw_test` | — |
| `QsfpTestRunner` | forwarding | `bin/qsfp_hw_test` | — |
| `LinkTestRunner` | forwarding | `bin/sai_mono_link_test-sai_impl`, `bin/sai_multi_link_test-sai_impl` | — |
| `PlatformTestRunner` | platform | the 7 platform `*_hw_test` binaries | no `share/`; `run_test.py` from image |
| `BspTestRunner` | platform | `bin/bsp_tests` | — |
| `SmokeTestRunner` | forwarding | `bin/python_tests/agent_smoke.py`, `bin/python_tests/junit.py` | runs the script directly — no `run_test.py`, no `share/` |
| `BenchmarkTestRunner` | forwarding | `bin/sai_all_benchmarks-sai_impl`, `bin/sai_multi_switch_all_benchmarks-sai_impl` | `share/hw_bench_configs/`; always invokes SAI benchmarks in multi_switch mode |

All forwarding runners get the full forwarding `share/` tree from `_STACK_SHARE`
(so `hw_benchmark_tests/sai_bench.materialized_JSON` is always present — the
earlier per-runner gap is gone).

For the **local** path, `_local_source_path` maps each deployed entry to its
source: compiled binaries come from `<build_dir>/build/fboss/`, while `share/`
configs come from the repo checkout (`fboss/oss/...`) — the same split
`package.py` uses.

## Benchmark agent run mode

The pytest hardware-test wrapper always invokes SAI benchmarks with:

```text
--agent-run-mode multi_switch
```

It deploys both SAI benchmark binaries so the forwarding artifact remains
compatible with the upstream benchmark runner.

Mono remains available for direct on-DUT invocations of `run_test.py`, but is
not selectable through this wrapper.

## Cache layout — runner host

```
<root>/fboss-test-cache/                 ← <root> = /workspace on TestEngine runners, else /tmp
└── <namespace>/                         ← Nexis build_id, or local-<fingerprint>
    ├── <tarball>/extracted/             ← Nexis only: downloaded+extracted tarball,
    │   └── bin/, share/, ...               shared by every runner on that build_id
    └── <RunnerName>-slice.tar           ← packed per deploy, removed after SCP
```

**Nexis path** — the tarball is downloaded+extracted once per `(build_id,
tarball)` and **shared across every runner type** on that build_id (all
forwarding runners reuse one extract), amortizing the expensive download+extract.

**Local path** — no extract cache. `_pack_slice` reads the binaries (from the
build dir) and `share/` configs (from the repo) straight into the slice tar via
`tarfile`, with each source's on-DUT path set as its archive name — no staging
copy is made to line the paths up.

Either way the per-runner slice is **not** cached: it's packed fresh, SCP'd, and
deleted (the DUT marker below already covers the repeat case).

The cache is **bounded to a single namespace**: before using one,
`_prune_stale_cache` deletes every other namespace dir, so it can't accumulate
builds on dev machines or long-lived TestEngine pods. (A Nexis batch runs against
one build, so all its runners share the build_id namespace and reuse the
extract.) The Nexis extract stages into a `staging/` dir then `os.rename`s it
into place, so an interrupted extract never leaves a partial dir mistaken for a
complete cache — this is crash safety, not concurrency handling (see below).

### Local namespace

The local namespace is `local-<fingerprint>`, where `_local_build_fingerprint`
digests the `(size, mtime_ns)` of just **this runner's uploaded sources** (its
`REQUIRED_PATHS` resolved through `_local_source_path`). It deliberately does
**not** use the build dir's own mtime: an in-place relink rewrites a binary
without touching the directory entry, so a dir-mtime namespace would mask a fresh
build. A file's own mtime always moves on rewrite, so any rebuilt binary this
runner ships bumps the namespace. It's stat-only (the binaries are ~1 GB each, so
hashing their bytes per setup would be far too slow), and `share/` config edits
without a rebuild don't move it (same caveat as the Nexis build_id). Because each
runner fingerprints its own slice, local runners get distinct namespaces.

## Cache layout — DUT (content-addressed)

```
/opt/fboss/                                  ← _FBOSS_ROOT_ON_DUT
├── bin/, lib/, share/                       ← production stack (from image)
└── .deployed/
    ├── SaiTestRunner.sha                    ← sha256 of the deployed slice
    └── BspTestRunner.sha
```

`.deployed/<RunnerName>.sha` holds the sha256 of the slice last deployed for
that runner. It's written **after** the slice extracts successfully (chained
`tar -xf ... && echo <sha> | tee <marker>` in one SSH call). On the next test
the runner packs its slice, hashes it, and `cat`s the marker: if the sha
matches, the exact same bytes are already on the DUT, so the SCP + on-DUT
extract are skipped. Content-addressed — no build_id, one file per runner
(overwritten), so it never accumulates.

## Lifecycle

| Layer | Cleared by | Survives |
| --- | --- | --- |
| Host cache (`<root>/fboss-test-cache/`, `<root>`=`/workspace` on runners else `/tmp`) | namespace change (auto-pruned to one build); volume/`/tmp` wipe on pod/host restart; manual `rm -rf` | within-pod nhtests-run invocations on the same build |
| DUT marker (`/opt/fboss/.deployed/`) | re-image (fresh `/opt/fboss`) | no-image prepare, switch reboot, between tests |

## Operator debug recipes

**Force a fresh deploy of one runner type on the DUT:**

```bash
ssh root@$DUT 'sudo rm -f /opt/fboss/.deployed/SaiTestRunner.sha'
```

**Wipe all DUT markers (next test of each runner type redeploys):**

```bash
ssh root@$DUT 'sudo rm -rf /opt/fboss/.deployed/'
```

**Clear the host cache entirely** (on a TestEngine runner use `/workspace/fboss-test-cache`):

```bash
rm -rf /tmp/fboss-test-cache        # dev machine
rm -rf /workspace/fboss-test-cache  # TestEngine runner
```

**Check what's actually on the DUT:**

```bash
ssh root@$DUT '
  ls /opt/fboss/.deployed/
  ls /opt/fboss/bin | grep -E "sai_test|qsfp_hw_test|bsp_tests|platform_hw_test"
'
```

## Concurrency

Not supported, by design. Concurrent runners within a single isolation domain
(container, VM, etc.) aren't a case we defend against — TestEngine serializes
DUT access per tenant, and a runner pod runs one `nhtests-run` at a time with
sequential tests. The `staging/` dir + `os.rename` in the cache writers exists
purely for **single-process crash safety** (a killed/failed extract never
publishes a partial `extracted/`), not for racing processes.

## Keeping the manifest in sync with upstream

Two guards catch drift from the upstream FBOSS test infra:

- **Binary names** — `test_runner_deploy.py` cross-checks every runner's
  `BINARIES` against the upstream `fboss_test_runner` package (`runners/*.py`).
  If upstream renames/removes a binary, or a `BINARIES` entry is mistyped, the
  test fails with a pointer to reconcile. Fix by editing the runner's `BINARIES`.
- **Deploy-time presence** — `_slice_members` checks every deployed path
  actually exists at its resolved source (the extracted tarball for Nexis, the
  build dir / repo for a local build) while building the pack list. A missing one
  raises:

  ```
  <Runner> REQUIRED_PATHS not found: ['bin/foo']. Either
  fboss/oss/scripts/package.py changed what it produces, or the
  runner's manifest is stale.
  ```

  Reconcile by editing `BINARIES` (binaries) or `_STACK_SHARE` (share configs).

`share/` rarely needs touching — `_STACK_SHARE` ships the whole forwarding tree,
so a new config file is picked up automatically.
