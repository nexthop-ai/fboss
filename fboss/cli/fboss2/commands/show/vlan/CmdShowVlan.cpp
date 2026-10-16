/*
 *  Copyright (c) 2004-present, Facebook, Inc.
 *  All rights reserved.
 *
 *  This source code is licensed under the BSD-style license found in the
 *  LICENSE file in the root directory of this source tree. An additional grant
 *  of patent rights can be found in the PATENTS file in the same directory.
 *
 */

#include "fboss/cli/fboss2/commands/show/vlan/CmdShowVlan.h"
#include "fboss/agent/if/gen-cpp2/FbossCtrlAsyncClient.h"
#include "fboss/cli/fboss2/CmdHandler.cpp"

#include <fboss/agent/if/gen-cpp2/FbossCtrl.h>
#include <folly/String.h>
#include <folly/Utility.h>
#include <thrift/lib/cpp2/protocol/Serializer.h>
#include <algorithm>
#include <cstdint>
#include <ostream>
#include <string>
#include <string_view>
#include <unordered_map>
#include <utility>
#include <vector>
#include "fboss/agent/gen-cpp2/agent_config_types.h"
#include "fboss/agent/gen-cpp2/switch_config_types.h"
#include "fboss/cli/fboss2/commands/show/vlan/gen-cpp2/model_types.h"
#include "fboss/cli/fboss2/utils/CmdClientUtilsCommon.h"
#include "fboss/cli/fboss2/utils/CmdUtils.h"
#include "fboss/cli/fboss2/utils/HostInfo.h"
#include "fboss/cli/fboss2/utils/Table.h"

namespace facebook::fboss {

namespace {
constexpr auto kNoneCell = "--";
constexpr auto kTagged = "tagged";
constexpr auto kUntagged = "untagged";

} // namespace

using utils::Table;
using RetType = CmdShowVlanTraits::RetType;

RetType CmdShowVlan::queryClient(const HostInfo& hostInfo) {
  auto client =
      utils::createClient<apache::thrift::Client<FbossCtrl>>(hostInfo);

  // There is no thrift API that lists VLANs with their member ports, so the
  // running config is the only source. sw.vlanPorts names its members by
  // numeric logicalPort, so createModel joins against sw.ports (for names) and
  // sw.interfaces (for addresses) -- the correlation users otherwise do by
  // hand across several `show config running agent | jq ...` invocations.
  std::string configStr;
  client->sync_getRunningConfig(configStr);

  cfg::AgentConfig agentConfig;
  apache::thrift::SimpleJSONSerializer::deserialize<cfg::AgentConfig>(
      configStr, agentConfig);
  // Handle the legacy case where the agent returns a bare SwitchConfig.
  if (*agentConfig.sw() == cfg::SwitchConfig()) {
    apache::thrift::SimpleJSONSerializer::deserialize<cfg::SwitchConfig>(
        configStr, *agentConfig.sw());
  }

  return createModel(*agentConfig.sw());
}

RetType CmdShowVlan::createModel(const cfg::SwitchConfig& swConfig) {
  RetType model;

  // logicalID -> port name, so members can be reported by name. Ports without
  // a name fall back to the numeric id rather than being dropped.
  std::unordered_map<int32_t, std::string> portNameById;
  for (const auto& port : *swConfig.ports()) {
    portNameById[*port.logicalID()] = port.name().has_value()
        ? *port.name()
        : std::to_string(*port.logicalID());
  }

  // vlanID -> members, ordered for display by utils::comparePortNameOrId
  // so output is stable across runs.
  std::unordered_map<int32_t, std::vector<cli::VlanMember>> membersByVlan;
  for (const auto& vlanPort : *swConfig.vlanPorts()) {
    cli::VlanMember member;
    member.logicalPort() = *vlanPort.logicalPort();
    const auto it = portNameById.find(*vlanPort.logicalPort());
    member.portName() = it != portNameById.end()
        ? it->second
        : std::to_string(*vlanPort.logicalPort());
    member.tagged() = *vlanPort.emitTags();
    membersByVlan[*vlanPort.vlanID()].push_back(member);
  }
  for (auto& vlanMembers : membersByVlan) {
    std::sort(
        vlanMembers.second.begin(),
        vlanMembers.second.end(),
        [](const cli::VlanMember& a, const cli::VlanMember& b) {
          return utils::comparePortNameOrId(
              *a.portName(), *a.logicalPort(), *b.portName(), *b.logicalPort());
        });
  }

  // The interface bound to a VLAN, indexed both ways. ThriftConfigApplier::
  // createVlan honours cfg::Vlan.intfID when it is set and only derives the
  // interface from sw.interfaces otherwise, so resolution below follows the
  // same precedence. The interface -- not cfg::Vlan -- is where IP addresses
  // live in current configs.
  std::unordered_map<int32_t, const cfg::Interface*> interfaceById;
  std::unordered_map<int32_t, const cfg::Interface*> interfaceByVlan;
  for (const auto& interface : *swConfig.interfaces()) {
    interfaceById.emplace(*interface.intfID(), &interface);
    if (*interface.type() == cfg::InterfaceType::VLAN) {
      interfaceByVlan.emplace(*interface.vlanID(), &interface);
    }
  }

  for (const auto& vlan : *swConfig.vlans()) {
    cli::VlanEntry entry;
    entry.vlanID() = *vlan.id();
    entry.name() = *vlan.name();
    entry.routable() = *vlan.routable();

    if (const auto members = membersByVlan.find(*vlan.id());
        members != membersByVlan.end()) {
      entry.members() = members->second;
    }

    // cfg::Vlan still carries ipAddresses for legacy configs, so report the
    // union of both sources rather than assuming one shape.
    std::vector<std::string> addresses = *vlan.ipAddresses();
    const cfg::Interface* interface = nullptr;
    if (vlan.intfID().has_value()) {
      entry.intfID() = *vlan.intfID();
      if (const auto it = interfaceById.find(*vlan.intfID());
          it != interfaceById.end()) {
        interface = it->second;
      }
    } else if (const auto it = interfaceByVlan.find(*vlan.id());
               it != interfaceByVlan.end()) {
      interface = it->second;
      entry.intfID() = *interface->intfID();
    }
    if (interface != nullptr) {
      for (const auto& address : *interface->ipAddresses()) {
        if (std::find(addresses.begin(), addresses.end(), address) ==
            addresses.end()) {
          addresses.push_back(address);
        }
      }
    }
    entry.ipAddresses() = std::move(addresses);

    // DHCP relay may be configured on the VLAN or on its interface; the VLAN
    // wins when both are set, matching how the agent reads cfg::Vlan first.
    if (vlan.dhcpRelayAddressV4().has_value()) {
      entry.dhcpRelayAddressV4() = *vlan.dhcpRelayAddressV4();
    } else if (interface && interface->dhcpRelayAddressV4().has_value()) {
      entry.dhcpRelayAddressV4() = *interface->dhcpRelayAddressV4();
    }
    if (vlan.dhcpRelayAddressV6().has_value()) {
      entry.dhcpRelayAddressV6() = *vlan.dhcpRelayAddressV6();
    } else if (interface && interface->dhcpRelayAddressV6().has_value()) {
      entry.dhcpRelayAddressV6() = *interface->dhcpRelayAddressV6();
    }

    model.vlans()->push_back(entry);
  }

  std::sort(
      model.vlans()->begin(),
      model.vlans()->end(),
      [](const cli::VlanEntry& a, const cli::VlanEntry& b) {
        return *a.vlanID() < *b.vlanID();
      });

  return model;
}

void CmdShowVlan::printOutput(const RetType& model, std::ostream& out) {
  Table outTable;
  outTable.setHeader(
      {"VLAN ID",
       "Name",
       "Routable",
       "Interface",
       "Members",
       "Tagging",
       "IP Addresses",
       "DHCP Relay V4",
       "DHCP Relay V6"});

  for (const auto& vlan : model.vlans().value()) {
    // Members and their tagging are emitted as parallel newline-joined cells
    // so each port lines up with its own tagging mode.
    std::vector<std::string> memberNames;
    std::vector<std::string> memberTagging;
    for (const auto& member : vlan.members().value()) {
      memberNames.push_back(member.portName().value());
      memberTagging.emplace_back(
          folly::copy(member.tagged().value()) ? kTagged : kUntagged);
    }

    outTable.addRow({
        std::to_string(folly::copy(vlan.vlanID().value())),
        vlan.name().value(),
        folly::copy(vlan.routable().value()) ? "Yes" : "No",
        vlan.intfID() ? std::to_string(*vlan.intfID()) : kNoneCell,
        memberNames.empty() ? kNoneCell : folly::join("\n", memberNames),
        memberTagging.empty() ? kNoneCell : folly::join("\n", memberTagging),
        vlan.ipAddresses()->empty() ? kNoneCell
                                    : folly::join("\n", *vlan.ipAddresses()),
        vlan.dhcpRelayAddressV4() ? *vlan.dhcpRelayAddressV4() : kNoneCell,
        vlan.dhcpRelayAddressV6() ? *vlan.dhcpRelayAddressV6() : kNoneCell,
    });
  }

  out << outTable << std::endl;
}

// Human description for auto-generated CLI reference wiki.
std::string_view CmdShowVlanTraits::description() {
  return "Displays the switch's VLANs and their member ports: each VLAN's ID, name, routable flag, bound interface, member ports with their tagging mode, IP addresses, and DHCP relay addresses. VLANs with no members are listed too.";
}

// Synthetic populated model for CLI reference wiki documentation.
RetType CmdShowVlan::sampleModel() {
  RetType model;

  cli::VlanEntry entry1;
  entry1.vlanID() = 10;
  entry1.name() = "fbossLoopback0";
  entry1.routable() = true;
  entry1.intfID() = 10;
  entry1.members() = {};
  entry1.ipAddresses() = {"10.254.113.31/32", "fc00:0:0:31::/128"};
  model.vlans()->push_back(entry1);

  cli::VlanMember member1;
  member1.portName() = "eth1/1/1";
  member1.logicalPort() = 1;
  member1.tagged() = true;

  cli::VlanMember member2;
  member2.portName() = "eth1/1/2";
  member2.logicalPort() = 2;
  member2.tagged() = false;

  cli::VlanEntry entry2;
  entry2.vlanID() = 2000;
  entry2.name() = "downlink";
  entry2.routable() = true;
  entry2.intfID() = 2000;
  entry2.members() = {member1, member2};
  entry2.ipAddresses() = {"192.168.0.1/24"};
  entry2.dhcpRelayAddressV4() = "10.1.1.1";
  entry2.dhcpRelayAddressV6() = "2401:db00::1";
  model.vlans()->push_back(entry2);

  return model;
}

// Explicit template instantiation
template void CmdHandler<CmdShowVlan, CmdShowVlanTraits>::run();
template const ValidFilterMapType
CmdHandler<CmdShowVlan, CmdShowVlanTraits>::getValidFilters();

} // namespace facebook::fboss
