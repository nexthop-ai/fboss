# fboss-sim - FBOSS Simulator Runtime

Minimal Docker runtime (~1.2 GB) for FBOSS with fake SAI — no hardware required.

## Quick Start

```bash
# 1. Enter the build container for your worktree
CT=$(docker ps --format '{{.Names}}' | grep "FBOSS_build.*$(basename $PWD)")

# 2. Build all required binaries with fake SAI (no vendor SDK needed)
docker exec "$CT" bash -lc \
  'cd /var/FBOSS/fboss && ./fboss/oss/scripts/bazel.sh build --sai fake \
   //fboss/agent/platforms/sai:wedge_agent-sai_impl \
   //fboss/agent/platforms/sai:fboss_hw_agent-sai_impl \
   //fboss/agent:fboss_sw_agent \
   //fboss/cli/fboss2:fboss2 \
   //fboss/cli/fboss2:fboss2-dev \
   "//fboss/cli/fboss2/test/integration_test:fboss2_integration_test"'

# 3. Collect binaries + libs, build runtime image
docker exec "$CT" python3 \
  /var/FBOSS/fboss/fboss-sim/scripts/fboss-sim-docker-package.py \
  --collect-only --bazel
docker build \
  -f fboss-sim/docker/Dockerfile.runtime \
  -t fboss_sim_runtime_${USER}:latest .

# 4. Start the container
python3 fboss-sim/scripts/fboss-sim-docker-run.py

# 5. Run integration tests
docker exec fboss_sim_runtime_${USER} \
  /opt/fboss/bin/fboss2_integration_test "--gtest_filter=-ConfigPfcTest.*"
```

> **cmake alternative** (still supported): replace steps 2-3 with
> `docker exec -e SAI_IMPL=fake $CT ./fboss/oss/scripts/nhfboss-build.sh ...`
> then `python3 fboss-sim/scripts/fboss-sim-docker-package.py` (no `--bazel`).

### Split build/host environments

When FBOSS is built inside a CentOS build container on a different-distro host
(e.g. Ubuntu) and you're not using the container-based flow above (e.g. cmake
mode run from the host), `ldd` must resolve libraries inside the container,
but `docker build` needs the host's Docker daemon. Run the two phases
separately:

```bash
# collect inside the build container (CentOS libs resolve correctly)
docker exec <build-container> python3 \
  fboss-sim/scripts/fboss-sim-docker-package.py --collect-only

# build the image on the host
python3 fboss-sim/scripts/fboss-sim-docker-package.py --build-only
```

## Agent Modes

**Split mode** (default): `fboss_sw_agent` + `fboss_hw_agent@0` run as separate systemd services.
The hw_agent connects to sw_agent over IPv6 (`::1`). This requires the container to have a
non-loopback IPv6 address — `fboss-sim-docker-run.py` handles this automatically by creating
a user-defined IPv6-enabled Docker network (`fboss_sim_net_${USER}`, subnet `fd00:fb05:5::/64`).

**Monolithic mode**: single `wedge_agent` process.
```bash
docker exec fboss_sim_runtime_${USER} switch-agent-mode.sh mono
```

## Useful Commands

```bash
# Check agent status
docker exec fboss_sim_runtime_${USER} systemctl status fboss_sw_agent
docker exec fboss_sim_runtime_${USER} systemctl status fboss_hw_agent@0

# View agent logs
docker exec fboss_sim_runtime_${USER} tail -f /var/facebook/logs/fboss/wedge_agent.log

# Run FBOSS CLI
docker exec fboss_sim_runtime_${USER} /opt/fboss/bin/fboss2 show interface

# Open a shell
docker exec -it fboss_sim_runtime_${USER} bash
```

## Architecture

```
fboss-sim/
├── docker/
│   ├── Dockerfile.runtime             # CentOS Stream 9 minimal runtime image
│   └── runtime/
│       ├── mono.conf                  # Monolithic agent config
│       ├── fruid.json                 # Platform identification (virtual env)
│       ├── setup-container.sh         # Runs at image build time: symlinks, jemalloc, services
│       └── switch-agent-mode.sh       # Toggle between split and monolithic mode
└── scripts/
    ├── fboss-sim-docker-package.py    # Collect binaries+libs (via ldd), build runtime image
    └── fboss-sim-docker-run.py        # Create IPv6 network, start runtime container
```

`Dockerfile.runtime` copies the FBOSS `centos-09.0` rootfs overlay
(`fboss-image/image_builder/templates/centos-09.0/root_files/`) for the systemd
layout — the agent units the simulator runs (`fboss_sw_agent`,
`fboss_hw_agent@`, the hw-agents target), the login-shell env hook, and the
eth0 IPv6 sysctl. That rootfs is part of the FBOSS tree, so this directory
builds identically inside or outside the Nexthop fork.

### How `fboss-sim-docker-package.py` works

Both modes share the same **collect** (`--collect-only`, or the first half of
a flagless run) and **build** (`--build-only`, or the second half) phase
split: collect resolves shared libraries via `ldd` and copies binaries,
libraries, and config files into `tmp_build_dir/` — this must run where the
resolved libs match the image base OS (CentOS Stream 9); build then builds the
Docker image from `Dockerfile.runtime` using `tmp_build_dir/` as context and
cleans up afterward.

**Bazel mode** (`--bazel`, recommended):
1. Resolves `bazel-bin/` symlinks to real ELF files, stages them flat in `tmp_bazel_stage/`
2. Runs the collect phase against that staging dir (typically inside the build
   container, so `ldd` resolves the right CentOS system libs)
3. Runs the build phase, then cleans up both staging dirs on completion

**cmake mode** (default, no `--bazel`):
Same as above but binaries are read directly from `.build_dir/build/fboss/`
instead of being staged from `bazel-bin/`.

### Why IPv6 matters for split mode

`folly::SocketAddress::setFromLocalPort()` calls `getaddrinfo(nullptr, port, AI_ADDRCONFIG)`.
`AI_ADDRCONFIG` only returns IPv6 results if the host has at least one non-loopback IPv6 address.
Docker's default bridge sets `net.ipv6.conf.eth0.disable_ipv6=1` per-interface, so containers
get no non-loopback IPv6 → Thrift servers bind to `0.0.0.0` only → hw_agent's connection to
`::1` is refused. The user-defined network with `--ipv6` prevents this.

## Binaries Included

| Binary | Purpose |
|--------|---------|
| `wedge_agent-sai_impl` | Monolithic agent (fake SAI) |
| `fboss_sw_agent` | Split mode: SW/control plane |
| `fboss_hw_agent-sai_impl` | Split mode: HW/forwarding plane (fake SAI) |
| `fboss2` | FBOSS CLI |
| `fboss2-dev` | FBOSS dev CLI |
| `fboss2_integration_test` | CLI integration test suite |
| `setup_fboss_env` | Environment setup helper |

## Container Capabilities

- `CAP_NET_ADMIN`: TUN interface creation (TunManager)
- `CAP_SYS_ADMIN`: systemd cgroup management
- `/dev/net/tun`: virtual network interfaces
- `--shm-size=512m`: shared memory for FBOSS IPC
