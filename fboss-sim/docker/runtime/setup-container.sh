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

# Copy split config as default agent.conf
echo "→ Installing split agent config..."
cp /root/config/split.conf /etc/coop/agent.conf

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

# 7. Enable split mode (fboss_sw_agent + fboss_hw_agent) by default
echo "→ Enabling split mode (fboss_sw_agent + fboss_hw_agent) by default..."
mkdir -p /etc/systemd/system/multi-user.target.wants
ln -sf /usr/lib/systemd/system/fboss_sw_agent.service \
  /etc/systemd/system/multi-user.target.wants/fboss_sw_agent.service
# Template instance: symlink name is the instance (@0), but target is the template (@)
ln -sf /usr/lib/systemd/system/fboss_hw_agent@.service \
  /etc/systemd/system/multi-user.target.wants/fboss_hw_agent@0.service

# Verify the symlinks were created
if [ -L /etc/systemd/system/multi-user.target.wants/fboss_sw_agent.service ] &&
  [ -L /etc/systemd/system/multi-user.target.wants/fboss_hw_agent@0.service ]; then
  echo "✓ fboss_sw_agent enabled"
  echo "✓ fboss_hw_agent@0 enabled"
else
  echo "✗ Failed to enable split agent services"
  exit 1
fi

# 8. Mask monolithic agent service (can be unmasked at runtime with switch-agent-mode.sh)
echo "→ Masking monolithic agent service..."
systemctl mask wedge_agent.service || true

# Note: Other FBOSS services (platform_manager, qsfp_service, etc.) are not enabled
# by default, so they won't start. No need to explicitly mask them.

echo ""
echo "=========================================="
echo "✅ Container Setup Complete!"
echo "=========================================="
echo ""
echo "Configuration Summary:"
echo "  - Split mode: ENABLED (fboss_sw_agent + fboss_hw_agent)"
echo "  - Monolithic mode: DISABLED (masked, use switch-agent-mode.sh to enable)"
echo "  - Memory allocator: jemalloc (via LD_PRELOAD)"
echo "  - Multi-switch flag: ENABLED (via /etc/coop/agent.conf)"
echo ""
