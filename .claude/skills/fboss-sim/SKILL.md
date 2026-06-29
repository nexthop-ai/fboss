---
name: fboss-sim
description: Build and test fboss-sim end-to-end on a workstation (fake-SAI only) — builds the FBOSS docker image and build container if missing, runs the fake-SAI build, builds/starts the fboss-sim runtime container, waits for the agent, and runs fboss2_integration_test. Never runs the real-SAI build.
when_to_use: |
  User asks to "run fboss-sim", "do the fake-SAI build", "run the integration
  test locally", or otherwise wants to build and test the simulator on their
  workstation — including from a fresh checkout where neither the docker
  image nor the build container exists yet.
---

# fboss-sim local build + test

Driver: [fboss-sim-build-and-test.sh](fboss-sim-build-and-test.sh) (lives in this
skill folder). Mirrors the **fake-SAI half** of `.github/workflows/build-and-test.yml`
— it never runs the real-SAI build, since fake-SAI is all the simulator needs.
Structured so it works from a fresh repo *or* an already-warmed workspace. Run it
from the repo root — its internal paths are resolved against the current working
directory.

## Stages

1. **Docker image** — `nhfboss-docker-build.py` if `fboss_image_${USER}:latest` is missing.
2. **Build container** — start `FBOSS_build_${USER}` (creates it via
   `nhfboss-docker-enter.py` if absent, `docker start` if stopped, no-op if
   already running).
3. **Ensure clean fake-SAI state** — `rm -rf` any stale fboss build/install dirs,
   `git checkout` the libsai/fboss manifests, `rm -f manifests/sai_impl`. Idempotent:
   no-ops on a fresh checkout, undoes a prior real-SAI build's leftovers otherwise.
4. **Fake-SAI build** — `nhfboss-get-deps.sh`, then `nhfboss-build.sh`
   `--cmake-target fboss_fake_agent_targets` and `fboss2_targets` with `SAI_IMPL=fake`.
5. **Runtime image + container** — `fboss-sim-docker-package.py` then
   `fboss-sim-docker-run.py`.
6. **Readiness poll** — `fboss2 show interface` for up to 10s; tails
   `wedge_agent.log` on timeout.
7. **Integration test** — `fboss2_integration_test` inside the runtime container.
8. **Cleanup** — runtime container/image/network and the build container.

## Invocation

```bash
.claude/skills/fboss-sim/fboss-sim-build-and-test.sh
```

Flags:
- `--sai-version V`    SAI version under `/var/extras/sai` (default `1.16.1`).
- `--full`             Re-run the real-SAI build even if artifacts look present.
- `--skip-test`        Build everything, skip `fboss2_integration_test`.
- `--keep-runtime`     Leave `fboss_sim_runtime_${USER}` running for debugging.
- `--no-cleanup-build` Leave `FBOSS_build_${USER}` running.

## Debugging

- Build failure: `docker exec -it FBOSS_build_${USER} bash`.
- Agent didn't come up: re-run with `--keep-runtime`, then
  `docker exec -it fboss_sim_runtime_${USER} bash` and inspect
  `/var/facebook/logs/fboss/wedge_agent.log`.
