# fboss-sim - FBOSS Simulator Runtime

Minimal, portable Docker runtime for FBOSS (Facebook Open Switching System) with fake SAI implementation.

## Quick Start

Build the complete fboss-sim runtime image in 6 steps:

```bash
# 1. Build FBOSS binaries (inside build container)
docker exec FBOSS_build_${USER} bash -c \
  "cd /var/FBOSS/fboss && \
   SAI_IMPL=fake ./fboss/oss/scripts/nhfboss-build.sh \
     --cmake-target fboss_forwarding_stack \
     --cmake-target fboss2_integration_test"

# 2. Package binaries with dependencies (inside build container)
docker exec FBOSS_build_${USER} bash -c \
  "cd /var/FBOSS/fboss && \
   ./fboss/oss/scripts/package-fboss.py \
     --scratch-path /var/FBOSS/tmp_bld_dir/ \
     --copy-root-libs \
     --compress"

# 3. Copy tarball to host (from ~/nh/fboss)
docker cp FBOSS_build_${USER}:/var/FBOSS/tmp_bld_dir/fboss_bins.tar.zst .build_dir/

# 4. Extract and build runtime image (from ~/nh/fboss)
./fboss-sim/scripts/fboss-sim-docker-package.py

# 5. Run the container (from ~/nh/fboss)
./fboss-sim/scripts/fboss-sim-docker-run.py

# 6. Verify it works
docker exec fboss_sim_runtime_${USER} /opt/fboss/bin/fboss2 --help
```

## What You Get

- **Minimal Runtime**: ~1.2 GB (vs 34 GB build environment)
- **7 Essential Binaries**: wedge_agent-fake, fboss_sw_agent, fboss_hw_agent-fake, fboss2, fboss2-dev, fboss2_integration_test, setup_fboss_env
- **35 System Libraries**: Automatically bundled with `--copy-root-libs`
- **Dual Agent Modes**: Monolithic (default) and split mode
- **Fake SAI**: No hardware required for testing

## Build Details

### Required Build Targets

```bash
# Forwarding stack (agents + core)
--cmake-target fboss_forwarding_stack

# CLI test binary
--cmake-target fboss2_integration_test
```

### Critical Flags

- `SAI_IMPL=fake` - Use fake SAI implementation (no hardware)
- `--copy-root-libs` - Bundle system libraries from `/lib64/` (libsodium, libdwarf, libre2, etc.)
- `--compress` - Create compressed tarball (~521 MB)

## Agent Modes

**Monolithic Mode** (default):
```bash
docker exec fboss_sim_runtime_${USER} systemctl start wedge_agent
```

**Split Mode**:
```bash
docker exec fboss_sim_runtime_${USER} switch-agent-mode.sh split
docker exec fboss_sim_runtime_${USER} systemctl start fboss_sw_agent
docker exec fboss_sim_runtime_${USER} systemctl start fboss_hw_agent
```

## Troubleshooting

**Missing libraries**: Re-run `package-fboss.py` with `--copy-root-libs`
**Build fails**: Run `./fboss/oss/scripts/nhfboss-get-deps.sh` first
**Container won't start**: Check `docker logs cfboss_runtime_${USER}`

## Architecture

```
fboss-sim/
├── README.md                          # This file
├── docker/
│   ├── Dockerfile.runtime             # Minimal runtime image (CentOS Stream 9)
│   └── runtime/
│       ├── mono.conf                  # Monolithic agent config
│       ├── fruid.json                 # Platform identification
│       ├── setup-container.sh         # Container initialization
│       └── switch-agent-mode.sh       # Mode switching script
└── scripts/
    ├── fboss-sim-docker-package.py    # Extract tarball and build runtime image
    └── fboss-sim-docker-run.py        # Run container

Note: Uses fboss/oss/scripts/package-fboss.py for binary packaging (step 2)
```

## Image Size Breakdown

- Base CentOS Stream 9: ~200 MB
- Runtime dependencies: ~150 MB
- FBOSS binaries (7): ~800 MB
- System libraries (35): ~50 MB
- **Total**: ~1.2 GB

## Security

Container runs with minimal capabilities:
- `CAP_NET_ADMIN`: Network interface management
- `CAP_SYS_ADMIN`: Systemd cgroup management
- `/dev/net/tun`: TUN device for virtual interfaces
