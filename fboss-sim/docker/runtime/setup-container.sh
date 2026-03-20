#!/bin/bash
# Container setup script for FBOSS base image
# This script configures the container environment for FBOSS agents
set -ex

echo "=========================================="
echo "FBOSS Container Setup"
echo "=========================================="

# 1. Make scripts executable
echo "→ Making scripts executable..."
chmod +x /usr/local/bin/* /opt/fboss/bin/* 2>/dev/null || true

# 2. Create symlinks for fake binaries to match production service expectations
echo "→ Creating symlinks for fake SAI binaries..."
ln -sf /opt/fboss/bin/wedge_agent-fake /opt/fboss/bin/wedge_agent-sai_impl
ln -sf /opt/fboss/bin/fboss_hw_agent-fake /opt/fboss/bin/fboss_hw_agent-sai_impl

# 3. Set environment (source setup_fboss_env if it exists)
echo "→ Configuring environment..."
if [ -f /opt/fboss/bin/setup_fboss_env ]; then
  echo "source /opt/fboss/bin/setup_fboss_env" >>/etc/profile.d/fboss.sh
fi

# 4. Initialize git repo in /etc/coop for config management
echo "→ Initializing git repo in /etc/coop..."
cd /etc/coop
git init
git config user.email "fboss@container"
git config user.name "FBOSS Container"

# Copy mono config as default agent.conf
echo "→ Installing mono agent config..."
cp /root/config/mono.conf /etc/coop/agent.conf

# 5. Configure services to use jemalloc instead of glibc malloc
# jemalloc is more robust against memory corruption issues in fake SAI
echo "→ Configuring jemalloc for all agent services..."
for service in wedge_agent.service fboss_sw_agent.service fboss_hw_agent@.service; do
  if [ -f /usr/lib/systemd/system/$service ]; then
    echo "  - Configuring $service"
    sed -i '/Environment="LD_LIBRARY_PATH/a Environment="LD_PRELOAD=/usr/lib64/libjemalloc.so.2"' \
      /usr/lib/systemd/system/$service
  fi
done

# 6. Reload systemd to pick up service changes
echo "→ Reloading systemd daemon..."
systemctl daemon-reload || true

# 7. Enable wedge_agent (monolithic mode) by default
echo "→ Enabling monolithic mode (wedge_agent) by default..."
mkdir -p /etc/systemd/system/multi-user.target.wants
ln -sf /usr/lib/systemd/system/wedge_agent.service \
  /etc/systemd/system/multi-user.target.wants/wedge_agent.service

# Verify the symlink was created
if [ -L /etc/systemd/system/multi-user.target.wants/wedge_agent.service ]; then
  echo "✓ wedge_agent enabled"
else
  echo "✗ Failed to enable wedge_agent"
  exit 1
fi

# 8. Mask split-agent services (can be unmasked at runtime with switch-agent-mode.sh)
echo "→ Masking split-agent services..."
systemctl mask fboss_sw_agent.service || true
systemctl mask fboss_hw_agent@0.service || true

# Note: Other FBOSS services (platform_manager, qsfp_service, etc.) are not enabled
# by default, so they won't start. No need to explicitly mask them.

echo ""
echo "=========================================="
echo "✅ Container Setup Complete!"
echo "=========================================="
echo ""
echo "Configuration Summary:"
echo "  - Monolithic mode: ENABLED (wedge_agent)"
echo "  - Split mode: DISABLED (masked, use switch-agent-mode.sh to enable)"
echo "  - Memory allocator: jemalloc (via LD_PRELOAD)"
echo "  - Multi-switch flag: ENABLED (via /etc/coop/agent.conf)"
echo ""
