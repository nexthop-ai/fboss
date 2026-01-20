#!/bin/bash

# getip.sh - MAC Address to IP Resolution Utility
#
# Description:
#   Resolves IP addresses (IPv4/IPv6) from MAC addresses using the kernel's
#   neighbor table (ARP/NDP cache). Supports optional network interface filtering.
#
# Usage:
#   getip.sh <MAC_ADDRESS> [INTERFACE]
#
# Algorithm:
#   1. Check neighbor table for existing MAC-to-IP mappings
#   2. If found: Ping specific IPs to verify and refresh the mapping
#   3. If not found: Ping broadcast (IPv4) and multicast (IPv6) to discover devices
#   4. Wait for neighbor table to update (1 second)
#   5. Query neighbor table again and return the IP address
#   6. Prioritize IPv4 over IPv6 in results
#
# Exit Codes:
#   0 - Success: IP address found and returned
#   1 - Error: MAC address not found in neighbor table
#   2 - Error: Invalid arguments or missing MAC address
#
# Dependencies:
#   - iproute2 (ip command)
#   - iputils (ping, ping6 commands)

print_usage() {
  cat <<EOF
Usage: $(basename "$0") [OPTIONS] <MAC_ADDRESS> [INTERFACE]

Get the IP address associated with a MAC address and an optional interface
from the ip neighbor table.

Arguments:
  MAC_ADDRESS    The MAC address to look up (e.g., aa:bb:cc:dd:ee:ff)
  INTERFACE      (Optional) The network interface to filter the search (e.g., eth0)

Options:
  -h             Show this help message and exit

Examples:
  $(basename "$0") aa:bb:cc:dd:ee:ff eth0
  $(basename "$0") aa:bb:cc:dd:ee:ff
  $(basename "$0") -h

EOF
}

# Get broadcast address for IPv4 from ip neighbor table or from local interfaces
get_ipv4_broadcast() {
  local target_intf="$1"
  local broadcast_ip=""
  local dev_option=""

  # Get broadcast IP from local interface configuration
  if [ -n "$target_intf" ]; then
    dev_option="dev $target_intf"
  fi
  broadcast_ip=$("ip -4 addr show ${dev_option}" | grep -oP 'brd \K[\d.]+' | head -n 1)
  echo "$broadcast_ip"
}

# Get link-local multicast address for IPv6
get_ipv6_multicast() {
  # Use all-nodes multicast address
  echo "ff02::1"
}

# Helper function to get IP from neighbor table for a given MAC address
# Args: $1=IP version (4 or 6), $2=MAC address, $3=dev_option (optional)
get_ip_from_neighbor() {
  local ip_version="$1"
  local target_mac="$2"
  local dev_option="$3"

  ip -"$ip_version" neighbor show $dev_option | grep -i "lladdr $target_mac" | awk '{print $1}' | head -n 1
}

# Helper function to ping an IP address with optional interface
# Args: $1=IP address, $2=interface (optional), $3=additional options (optional)
ping_ip() {
  local ip_addr="$1"
  local target_intf="$2"
  local extra_options="$3"
  local ping_cmd="ping"
  local ping_options="-c 1 -w 1"

  # Determine if IPv6 based on presence of colon in IP
  if [[ $ip_addr =~ : ]]; then
    ping_cmd="ping6"
  fi

  # Add extra options if provided (e.g., -b for broadcast)
  if [ -n "$extra_options" ]; then
    ping_options="$extra_options $ping_options"
  fi

  # Add interface option if provided
  if [ -n "$target_intf" ]; then
    ping_options="$ping_options -I $target_intf"
  fi

  $ping_cmd $ping_options "$ip_addr" >/dev/null 2>&1
}

# Check if an IP is IPv6
is_ipv6() {
  local ip="$1"
  [[ $ip =~ : ]]
}

get_ip_from_mac() {
  local target_mac="$1"
  local target_intf="$2" # Optional interface argument

  # Build device option for ip commands
  local dev_option=""
  if [ -n "$target_intf" ]; then
    dev_option="dev $target_intf"
  fi

  # Step 1: Check the neighbor table for existing entries (both IPv4 and IPv6)
  # Check for IPv4 entry
  local existing_ipv4=""
  existing_ipv4=$(get_ip_from_neighbor 4 "$target_mac" "$dev_option")
  # Check for IPv6 entry
  local existing_ipv6=""
  existing_ipv6=$(get_ip_from_neighbor 6 "$target_mac" "$dev_option")

  if [ -n "$existing_ipv4" ] || [ -n "$existing_ipv6" ]; then
    # Entry exists, ping the specific IP(s) to verify the MAC-IP mapping
    [ -n "$existing_ipv4" ] && ping_ip "$existing_ipv4" "$target_intf"
    [ -n "$existing_ipv6" ] && ping_ip "$existing_ipv6" "$target_intf"
  else
    # Entry doesn't exist, ping the broadcast/multicast addresses

    # Ping IPv4 broadcast if we have one
    local broadcast_ipv4=""
    broadcast_ipv4=$(get_ipv4_broadcast "$target_intf")
    [ -n "$broadcast_ipv4" ] && ping_ip "$broadcast_ipv4" "$target_intf" "-b"

    # Ping IPv6 multicast address
    local multicast_ipv6=""
    multicast_ipv6=$(get_ipv6_multicast)
    ping_ip "$multicast_ipv6" "$target_intf"
  fi

  # Wait a moment for the neighbor table to update
  sleep 1

  # Step 2: Check the neighbor table again and return all IPs which match the MAC
  # Get IPv4 address
  local ipv4_addr=""
  ipv4_addr=$(get_ip_from_neighbor 4 "$target_mac" "$dev_option")
  # Get IPv6 address
  local ipv6_addr=""
  ipv6_addr=$(get_ip_from_neighbor 6 "$target_mac" "$dev_option")

  # Return IPv4 first if available, otherwise IPv6
  if [ -n "$ipv4_addr" ]; then
    echo "$ipv4_addr"
  elif [ -n "$ipv6_addr" ]; then
    echo "$ipv6_addr"
  fi
}

# Parse arguments
if [ "$1" = "-h" ] || [ "$1" = "--help" ]; then
  print_usage
  exit 0
fi

if [ -z "$1" ]; then
  echo "Error: MAC address argument required. Use -h for help." >&2
  echo "" >&2
  print_usage
  exit 2
fi

# Get the IP address for the provided MAC address (and optional interface)
result_ip=$(get_ip_from_mac "$@")
if [ -n "$result_ip" ]; then
  echo "$result_ip"
  exit 0
else
  if [ -n "$2" ]; then
    echo "MAC address $1 not found in ip neighbor table on interface $2."
  else
    echo "MAC address $1 not found in ip neighbor table."
  fi
  exit 1
fi
