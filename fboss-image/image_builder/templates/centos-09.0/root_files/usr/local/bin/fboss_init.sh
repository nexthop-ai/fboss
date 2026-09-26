#!/bin/bash
# Initialize FBOSS configuration based on platform detection

set -e

# shellcheck source=/opt/fboss/bin/setup_fboss_env
source /opt/fboss/bin/setup_fboss_env

FBOSS_SHARE="/opt/fboss/share"
COOP_DIR="/etc/coop"
FRUID_FILE="/var/facebook/fboss/fruid.json"
CHASSIS_EEPROM_PARSED="/run/devmap/eeproms/CHASSIS_EEPROM_PARSED"
# Passed as --flagfile by the fboss_sw_agent, fboss_hw_agent@ and qsfp_service
# units; on tmpfs so it cannot go stale across boots.
VARIANT_FLAGFILE="/run/fboss/variant_flags"
NPU_SDK_UTILS_TOOL="/opt/fboss/bin/npu_sdk_utils.py"
NPU_SDK_METADATA="${FBOSS_SHARE}/npu_sdk_metadata.json"
NPU_HW_AGENT_BINARY="fboss_hw_agent-sai_impl"

log() {
  echo "[fboss_init] $1" >&2
}

error() {
  echo "[fboss_init] ERROR: $1" >&2
}

get_platform_dir() {
  local platform
  # for cFBOSS the platform name is provided via a marker file
  if [[ -f /etc/fboss/platform ]]; then
    platform=$(tr -d '[:space:]' </etc/fboss/platform | tr '[:upper:]' '[:lower:]')
    if [[ -z $platform ]]; then
      error "Empty /etc/fboss/platform"
      return 1
    fi
    log "Detected platform from /etc/fboss/platform: $platform"
  else
    # convert the platform name to lowercase and delete spaces
    platform=$(dmidecode -s system-product-name 2>/dev/null | tr '[:upper:]' '[:lower:]' | tr -d '[:space:]-_')
    if [[ -z $platform ]]; then
      error "Failed to get system-product-name from dmidecode"
      return 1
    fi
    log "Detected platform: $platform"
  fi

  # Map DMI platform names to config directory names where they differ.
  local config_name
  config_name=$(map_platform_to_config "$platform")
  log "Config name: $config_name"

  local platform_dir="${FBOSS_SHARE}/default_configs/${config_name}"
  if [[ ! -d $platform_dir ]]; then
    error "Platform config directory not found: $platform_dir"
    return 1
  fi
  log "Using platform config directory: $platform_dir"

  echo "$platform_dir"
}

map_platform_to_config() {
  local platform="$1"
  declare -A platform_map=(
    # Steller Eagle (m4062nhp): early units have "Nova4000" burned into the
    # BIOS SMBIOS product name, which dmidecode still reports, so map the
    # legacy name to the renamed config dir (NOS-6469). Units reporting
    # "M4062NHP" resolve to the same dir via the default below.
    ["nova4000"]="m4062nhp"
  )
  echo "${platform_map[$platform]:-$platform}"
}

copy_config() {
  local src="$1"
  local dst="$2"
  local name="$3"

  if [[ -e $dst ]]; then
    log "$name already exists at $dst (skipping)"
    return
  fi

  if [[ -f $src ]]; then
    cp "$src" "$dst"
    log "Copied $name: $src -> $dst"
  else
    log "No $name found at $src (skipping)"
  fi
}

setup_agent_config() {
  local src="$1"
  local dst="${COOP_DIR}/agent.conf"

  if [[ -e $dst ]]; then
    log "agent.conf already exists at $dst (skipping)"
    return
  fi

  if [[ ! -f $src ]]; then
    log "No agent.conf found at $src (skipping)"
    return
  fi

  # Fake-SAI artifacts intentionally do not carry NPU SDK metadata.
  if [[ ! -f $NPU_SDK_METADATA ]]; then
    log "No NPU SDK metadata found; keeping the configured SDK version"
    copy_config "$src" "$dst" "agent.conf"
    return
  fi

  python3 "$NPU_SDK_UTILS_TOOL" materialize-agent-config \
    --config-path "$src" \
    --metadata-path "$NPU_SDK_METADATA" \
    --binary-name "$NPU_HW_AGENT_BINARY" \
    --output-directory "$COOP_DIR"
  log "Created agent.conf for $NPU_HW_AGENT_BINARY"
}

generate_fruid() {
  if [[ -s $FRUID_FILE ]]; then
    log "Non-empty fruid.json already exists at $FRUID_FILE (skipping)"
    return
  fi

  mkdir -p "$(dirname "$FRUID_FILE")"

  if weutil --json >"$FRUID_FILE"; then
    log "Generated fruid.json: $FRUID_FILE"
  else
    error "Failed to generate fruid.json"
    rm -f "$FRUID_FILE"
    return 1
  fi
}

setup_coop_configs() {
  local platform_dir="$1"
  # /etc/coop is created with the right ownership, setgid bit, and default
  # ACL at image-build time (config.sh); re-assert it here in case it's ever
  # missing or drifted. The setgid bit (mode 2775) makes new entries created
  # by individual operators (via `fboss2-dev config`) inherit the switching
  # group; the default ACL forces group rwx on new entries regardless of the
  # creating operator's umask.
  mkdir -p "$COOP_DIR"
  chown coop:switching "$COOP_DIR"
  chmod 2775 "$COOP_DIR"
  setfacl -m g:switching:rwx "$COOP_DIR"
  setfacl -d -m g:switching:rwx -m o::rx "$COOP_DIR"
  setup_agent_config "${platform_dir}/agent.conf"
  copy_config "${platform_dir}/qsfp.conf" "${COOP_DIR}/qsfp.conf" "qsfp.conf"
  copy_config "${platform_dir}/led.conf" "${COOP_DIR}/led.conf" "led.conf"
}

get_eeprom_field() {
  if [[ -r $CHASSIS_EEPROM_PARSED ]]; then
    sed -n "s|^$1: *||p" "$CHASSIS_EEPROM_PARSED" | head -1
  fi
}

# Derive the platform-descriptor variant gflag (variantAttributes) from the
# chassis hardware revision, so agents never read the EEPROM themselves. A box
# missing any field gets no flag and falls back to the default descriptor.
set_variant_flags() {
  local state substate respin
  state=$(get_eeprom_field "Production State")
  substate=$(get_eeprom_field "Production Sub-State")
  respin=$(get_eeprom_field "Re-Spin/Variant Indicator")
  log "Chassis hardware revision: state=${state:-none} substate=${substate:-none} respin=${respin:-none}"

  if [[ -z $state || -z $substate || -z $respin ]]; then
    rm -f "$VARIANT_FLAGFILE"
    return
  fi

  mkdir -p "$(dirname "$VARIANT_FLAGFILE")"
  echo "--hwrev_state${state}_substate${substate}_respin${respin}=true" >"$VARIANT_FLAGFILE"
  log "Wrote $VARIANT_FLAGFILE"
}

enable_hw_agents() {
  local platform_dir="$1"
  local num_hw_agents
  if [ ! -f "${platform_dir}/num_hw_agents" ]; then
    num_hw_agents=1
  else
    num_hw_agents=$(cat "${platform_dir}/num_hw_agents")
  fi
  for i in $(seq ${num_hw_agents}); do
    systemctl enable "fboss_hw_agent@$((i - 1)).service"
    # Synchronous systemctl start inside a starting systemd service deadlocks on
    # dependency resolution. --no-block enqueues to start the job.
    systemctl start --no-block "fboss_hw_agent@$((i - 1)).service"
  done
}

create_distro_base_snapshot() {
  local base_snapshot="/distro-base"

  if [[ -e $base_snapshot ]]; then
    log "Base snapshot already exists at $base_snapshot (skipping)"
    return
  fi

  log "Creating base snapshot for service updates..."
  if btrfs subvolume snapshot / "$base_snapshot"; then
    log "Created $base_snapshot snapshot successfully"
    # Make it read-only to prevent accidental modifications
    if btrfs property set -ts "$base_snapshot" ro true; then
      log "Set $base_snapshot to read-only"
    else
      error "Failed to set $base_snapshot to read-only"
      return 1
    fi
  else
    error "Failed to create $base_snapshot snapshot"
    return 1
  fi
}

main() {
  log "Starting FBOSS initialization"

  local platform_dir
  if ! platform_dir=$(get_platform_dir); then
    exit 1
  fi

  # skip snapshot for cFBOSS docker image
  local platform_name
  platform_name=$(basename "$platform_dir")
  if [[ $platform_name != "cfboss" ]]; then
    create_distro_base_snapshot
  fi

  setup_coop_configs "$platform_dir"
  set_variant_flags
  if ! generate_fruid; then
    exit 1
  fi
  enable_hw_agents "$platform_dir"

  log "FBOSS initialization complete"
}

main "$@"
