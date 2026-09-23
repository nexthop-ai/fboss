<<<<<<< HEAD
# Instructions

- Do not pipe commands to head/tail/grep etc, redirect the output to a /tmp file and then check $? to see if the command succeeded and then filter the output by running head/tail/grep etc on the /tmp file.

## Building and testing

- To build the code, don't invoke cmake directly, use this script: ./fboss/oss/scripts/nhfboss-build.sh
- To build a specific target use ./fboss/oss/scripts/nhfboss-build.sh --cmake-target <name>
- If the build fails with SAI_EXPERIMENTAL_INCLUDE_DIR-NOTFOUND the SAI tarball at /var/extras/sai/$SAI_VERSION/libsai_impl.tar.gz was not found or is inaccessible; nhfboss-build.sh passes it automatically via --npu-libsai-impl-tarball so just ensure the file exists
- If there are issues with missing dependencies, you need to run ./fboss/oss/scripts/nhfboss-get-deps.sh and then retry running ./fboss/oss/scripts/nhfboss-build.sh
- You never need to manually build or delete anything under /var/FBOSS/tmp_bld_dir/
- To run the tests, use this script: ./fboss/oss/scripts/nhfboss-test.sh --timeout 30 --retry 0
- To run a subset of the tests, additionally pass --filter <regexp> where the regexp is matching the test case name in the code, not the cmake target.
- Always rebuild the code and the test binary and re-run unit tests to check your work.
- This project uses both cmake and BUCK, however we cannot build it with BUCK. Changes made to cmake files must also be reflected in the corresponding BUCK files, even though we cannot test them. Make sure the files are listed alphabetically.
- The build unfortunately changes some files under build/fbcode_builder/manifests, make sure you don't commit or revert those files unless otherwise explicitly instructed, in particular don't use git commit -a or git add -u
- To run end to end tests, you need to use a real FBOSS device, usually we use fboss101 but if you're not sure ask which device to use. You need to scp the fboss2-dev binary to the device e.g. scp /var/FBOSS/tmp_bld_dir/build/fboss/fboss2-dev fboss101:~/benoit/fboss2-dev (if you modified some of the end to end test Python scripts you need to scp them also under /opt/fboss/share/) and then run the end to end tests by executing the following command over ssh on fboss101 or whichever test device we're using: cd /opt/fboss && FBOSS_CLI_PATH=/home/netops/benoit/fboss2-dev ./bin/run_test.py cli

## Coding rules

- Use fmt::format instead of doing string concatenation.
- Don't use libc or stdlib functions that are not reentrant or thread safe. For example use folly::errnoStr() instead of strerror().
- Don't use std::regex, use RE2 instead.
- Whenever possible use existing strong typedefs from fboss/agent/types.h especially for things like interface IDs, port IDs, vlan IDs, etc.
- If possible avoid calling c_str() on std::string if not needed, in particular when passing it as a folly::StringPiece.
- Don't use .has_value() on Thrift non-optional fields.
- If a function may return a nullable pointer, it must be marked nullable by annotating the return type with FOLLY_NULLABLE defined in <folly/CppAttributes.h>.
||||||| a86baef3b7
=======
# AGENTS.md

Guidance for AI coding agents working in this repository.

FBOSS (Facebook Open Switching System) is switch software: `agent` (ASIC
control via SAI), `qsfp_service` (optics), platform services (sensors, fans,
LEDs, firmware), the `fboss2` CLI, and FSDB (state distribution).

## Skills

`fboss/skills/` contains task-specific workflow guides — debugging agent
hardware tests, applying FBOSS coding standards, and reviewing changes. Read
`fboss/skills/README.md` first, then load a skill's `SKILL.md` when its task
matches what you are doing. Prefer these over improvising a workflow.

## Layout

| Path | Contents |
|------|----------|
| `fboss/agent/` | Core agent; `hw/sai/` SAI implementation, `hw/switch_asics/` per-ASIC support |
| `fboss/platform/` | Platform services (sensors, fans, LEDs, firmware) |
| `fboss/configs/platforms/` | Per-platform mapping sources, by vendor and platform |
| `fboss/qsfp_service/` | Transceiver management |
| `fboss/cli/fboss2/` | Command line interface |
| `fboss/fsdb/` | State database |
| `fboss/lib/` | Shared libraries; `platform_mapping_v2/` generates the mappings |
| `fboss/oss/` | Build scripts, test configs, SDK versions |
| `fboss/skills/` | Agent workflow guides |

## Build

FBOSS builds inside a container. See the build documentation at
https://facebook.github.io/fboss/ for current commands; the runnable snippets
live in `docs/static/code_snips/`.

- The container image (`fboss/oss/docker/Dockerfile`) provides the toolchain
  and system packages. Do not install build dependencies on the host.
- Builds are memory-hungry. If compilation dies unexpectedly, lower
  parallelism before assuming a compiler or source problem.
- Do not delete the getdeps scratch directory to "fix" a build. It forces a
  full rebuild and rarely addresses the actual failure.
- Forwarding-stack builds against a real vendor SDK require a precompiled
  `libsai_impl.a` and its matching SAI headers. With no SAI implementation
  selected the build uses fake SAI instead, which needs no vendor artifact.
  See `fboss/oss/scripts/run-getdeps.py -h` for the implementation and SDK
  version flags.

## Test

Unit tests and fake-SAI tests run without hardware. Anything named
`*_hw_test` or `sai_test` built against a real SDK requires a switch.

Known-bad and unsupported test lists live under `fboss/oss/`.

## Conventions

- End every file with a trailing newline; use unix line endings.
- Never edit files marked `@generated`.
- Platform mapping JSON is generated into a `generated/` subdirectory. Edit
  the CSVs in `fboss/configs/platforms/<vendor>/<platform>/platform_mapping/`
  (or `.../<platform>/variants/<variant>/platform_mapping/`) and never edit
  anything under `generated/`. Note that `<platform>_vendor_config.json`,
  which sits beside the CSVs, is hand-maintained rather than generated.
- Thrift files generate code. Regenerate rather than hand-editing output.

## Not in this repository

This repository does not contain the Buck build, Meta-internal configuration,
Meta-internal test infrastructure, or Meta-internal CI. If a document or code
comment references those, it applies only to internal checkouts.

For questions, use GitHub Issues or Discussions.
>>>>>>> 7645153f2671a8414e17f720188a6810f8fcc177
