# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

FBOSS (Facebook Open Switching System) is Facebook's software stack for controlling and managing network switches. The agent daemon runs on each switch and controls the hardware forwarding ASIC, sending forwarding information to hardware and implementing control plane protocols (ARP, NDP). The agent provides thrift APIs for external routing control processes.

Documentation: https://facebook.github.io/fboss/ (source in `docs/docs/`)

## Build System

### Building the Code

**Do not invoke cmake directly.** Use the build script:

```bash
./fboss/oss/scripts/nhfboss-build.sh
```

Build a specific target:

```bash
./fboss/oss/scripts/nhfboss-build.sh --cmake-target <name>
```

### First-Time Setup

If the build fails with `SAI_EXPERIMENTAL_INCLUDE_DIR-NOTFOUND`, run this one-time initialization:

```bash
./fboss/oss/scripts/build-helper.py /var/extras/sai/1.16.1 /var/extras/sai/1.16.1 /var/extras/sai/1.16.1 1.16.1 --skip-archive-creation
```

### Dependencies

If dependencies are missing:

```bash
./fboss/oss/scripts/nhfboss-get-deps.sh
```

Never manually build or delete anything under `/var/FBOSS/tmp_bld_dir/`.

### Testing

Run all tests:

```bash
./fboss/oss/scripts/nhfboss-test.sh --timeout 30 --retry 0
```

Run subset of tests (regexp matches test case name in code, not cmake target):

```bash
./fboss/oss/scripts/nhfboss-test.sh --timeout 30 --retry 0 --filter <regexp>
```

Always rebuild the code and re-run unit tests to check your work.

### Build System Notes

- Uses CMake (primary build system) and Buck (Buck cannot build this project)
- Changes to cmake files must be reflected in corresponding BUCK files, with files listed alphabetically
- The build modifies files under `build/fbcode_builder/manifests` - do not commit or revert these files unless explicitly instructed
- Do not use `git commit -a` or `git add -u` due to build artifacts

## Architecture

### Core Components

- **fboss/agent/**: Agent daemon that controls the hardware ASIC
  - **hw/**: Hardware abstraction layer
    - **bcm/**: Broadcom-specific implementation
    - **sai/**: Switch Abstraction Interface (SAI) implementation
    - **sim/**: Simulator
    - **switch_asics/**: ASIC-specific code
  - **platforms/**: Platform-specific code for different switch hardware
  - **state/**: State management
  - **rib/**: Routing Information Base (RIB) - manages routing tables and FIB updates
  - **if/**: Thrift interface definitions
  - **configs/**: Sample configuration files (JSON)

- **common/**: Shared libraries
  - **network/**: Network utilities
  - **logging/**: Logging infrastructure
  - **fb303/**: Facebook's common service framework
  - **stats/**: Statistics collection

- **docs/**: Docusaurus-based documentation website

### Thrift-Based Architecture

FBOSS uses Thrift extensively for APIs and data structures. Key thrift files:
- Agent control: `fboss/agent/if/`
- Hardware interfaces: `fboss/agent/hw/*/`
- Configuration: `fboss/agent/agent_config.thrift`, `fboss/agent/platform_config.thrift`

## Coding Conventions

### Required Practices

- Use `fmt::format` instead of string concatenation
- Use thread-safe functions: `folly::errnoStr()` instead of `strerror()`
- Use RE2 instead of `std::regex`
- Use strong typedefs from `fboss/agent/types.h` (interface IDs, port IDs, VLAN IDs)
- Avoid calling `.c_str()` on `std::string` when passing as `folly::StringPiece`
- Do not use `.has_value()` on Thrift non-optional fields
- Mark nullable return pointers with `FOLLY_NULLABLE` from `<folly/CppAttributes.h>`

### Code Quality

Pre-commit hooks enforce:
- clang-format for C++ (uses `.clang-format`)
- black for Python
- shellcheck and shfmt for shell scripts
- Trailing whitespace, EOF fixers
- YAML/JSON validation

## Command Output Handling

Do not pipe commands to head/tail/grep directly. Instead:
1. Redirect output to a `/tmp` file
2. Check `$?` to verify command succeeded
3. Filter the output by running head/tail/grep on the `/tmp` file

This ensures you can verify command success before processing output.
