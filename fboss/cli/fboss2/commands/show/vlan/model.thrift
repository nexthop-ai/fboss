package "facebook.com/fboss/cli"

namespace cpp2 facebook.fboss.cli

struct ShowVlanModel {
  1: list<VlanEntry> vlans;
}

// One port's membership of a VLAN. `portName` is resolved from the numeric
// logicalPort that cfg::VlanPort carries, so callers never have to join
// against sw.ports themselves.
struct VlanMember {
  1: string portName;
  2: i32 logicalPort;
  3: bool tagged;
}

struct VlanEntry {
  1: i32 vlanID;
  2: string name;
  3: bool routable;
  // Interface bound to this VLAN, when one exists. IP addresses live on that
  // interface rather than on cfg::Vlan in current configs.
  4: optional i32 intfID;
  5: list<VlanMember> members;
  6: list<string> ipAddresses;
  7: optional string dhcpRelayAddressV4;
  8: optional string dhcpRelayAddressV6;
}
