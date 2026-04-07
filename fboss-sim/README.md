# fboss-sim - FBOSS Simulator Runtime

Minimal Docker runtime (~1.2 GB) for FBOSS with fake SAI — no hardware required.

## Quick Start

```bash
# 1. Build FBOSS with fake SAI (inside build container)
docker exec -e SAI_IMPL=fake FBOSS_build_${USER} \
  ./fboss/oss/scripts/nhfboss-build.sh --cmake-target fboss_fake_agent_targets
docker exec -e SAI_IMPL=fake FBOSS_build_${USER} \
  ./fboss/oss/scripts/nhfboss-build.sh --cmake-target fboss2_targets

# 2. Build runtime image (collects deps via ldd, builds Docker image)
python3 fboss-sim/scripts/fboss-sim-docker-package.py

# 3. Start the container
python3 fboss-sim/scripts/fboss-sim-docker-run.py

# 4. Run integration test
docker exec fboss_sim_runtime_${USER} /opt/fboss/bin/fboss2_integration_test
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

### How `fboss-sim-docker-package.py` works

1. Verifies required binaries exist in `.build_dir/build/fboss/`
2. Runs `--collect-only` inside the build container (CentOS) so `ldd` resolves the right system libs
3. Copies binaries, resolved shared libraries, and config files into `tmp_build_dir/`
4. Builds the Docker image from `Dockerfile.runtime` using `tmp_build_dir/` as context
5. Cleans up `tmp_build_dir/` on completion

### Why IPv6 matters for split mode

`folly::SocketAddress::setFromLocalPort()` calls `getaddrinfo(nullptr, port, AI_ADDRCONFIG)`.
`AI_ADDRCONFIG` only returns IPv6 results if the host has at least one non-loopback IPv6 address.
Docker's default bridge sets `net.ipv6.conf.eth0.disable_ipv6=1` per-interface, so containers
get no non-loopback IPv6 → Thrift servers bind to `0.0.0.0` only → hw_agent's connection to
`::1` is refused. The user-defined network with `--ipv6` prevents this.

## Binaries Included

| Binary | Purpose |
|--------|---------|
| `wedge_agent-fake` | Monolithic agent (fake SAI) |
| `fboss_sw_agent` | Split mode: SW/control plane |
| `fboss_hw_agent-fake` | Split mode: HW/forwarding plane (fake SAI) |
| `fboss2` | FBOSS CLI |
| `fboss2-dev` | FBOSS dev CLI |
| `fboss2_integration_test` | CLI integration test suite |
| `setup_fboss_env` | Environment setup helper |

## Container Capabilities

- `CAP_NET_ADMIN`: TUN interface creation (TunManager)
- `CAP_SYS_ADMIN`: systemd cgroup management
- `/dev/net/tun`: virtual network interfaces
- `--shm-size=512m`: shared memory for FBOSS IPC
