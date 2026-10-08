// (c) Nexthop Systems, Inc. and affiliates. Confidential and proprietary.

#include <folly/IPAddressV6.h>
#include <folly/MacAddress.h>
#include <folly/logging/xlog.h>

#include "fboss/agent/packet/EthHdr.h"
#include "fboss/agent/packet/IPv6Hdr.h"
#include "fboss/agent/packet/PktFactory.h"
#include "fboss/agent/packet/UDPHeader.h"
#include "fboss/agent/state/PortDescriptor.h"
#include "fboss/agent/test/link_tests/AgentEnsembleLinkTest.h"
#include "fboss/lib/CommonUtils.h"

namespace facebook::fboss {

namespace {
constexpr auto kSrcIpV6 = "2401:db00:2110:3001::1";
constexpr auto kDstIpV6 = "2401:db00:2110:3001::2";
constexpr uint16_t kSrcPort = 47231;
constexpr uint16_t kDstPort = 8000;
constexpr int kFcsSize = 4;
constexpr int kNumPkts = 100;
} // namespace

// Verifies ingress unicast counters track received packets across a range of
// frame sizes. Needs cabled ports: ingress packet counters may not be populated
// on a port in MAC loopback.
class AgentEnsembleJumboFrameCounterTest : public AgentEnsembleLinkTest {
 protected:
  std::vector<link_test_production_features::LinkTestProductionFeature>
  getProductionFeatures() const override {
    return {
        link_test_production_features::LinkTestProductionFeature::L2_LINK_TEST};
  }

  // Frame size on the wire, as the MAC counters see it.
  static int wireFrameSize(int payloadSize) {
    return static_cast<int>(EthHdr::SIZE) + static_cast<int>(IPv6Hdr::SIZE) +
        UDPHeader::size() + payloadSize + kFcsSize;
  }

  // Switch MAC as DA so the frame is routed on the peer's ingress rather than
  // dropped.
  void sendPkt(int payloadSize, PortID txPort, folly::MacAddress mac) {
    auto txPacket = utility::makeUDPTxPacket(
        getSw(),
        getSw()->getState()->getVlans()->getFirstVlanID(),
        mac,
        mac,
        folly::IPAddressV6(kSrcIpV6),
        folly::IPAddressV6(kDstIpV6),
        kSrcPort,
        kDstPort,
        0,
        255,
        std::vector<uint8_t>(payloadSize, 0xff));
    getAgentEnsemble()->sendPacketAsync(
        std::move(txPacket), PortDescriptor(txPort), std::nullopt);
  }

  void runIngressCounterTest(const std::vector<int>& payloadSizes) {
    auto connectedPairs = getConnectedPairs();
    if (connectedPairs.empty()) {
      GTEST_SKIP() << "No cabled port pairs; this test needs a real link";
    }
    auto [txPort, rxPort] = *connectedPairs.begin();
    auto switchId = getSw()->getScopeResolver()->scope(txPort).switchId();
    auto mac = getSw()->getLocalMac(switchId);

    programDefaultRoute(getSingleVlanOrRoutedCabledPorts(switchId), mac);

    XLOG(INFO) << "txPort=" << txPort << " rxPort=" << rxPort
               << " mac=" << mac.toString();

    for (auto payloadSize : payloadSizes) {
      auto before = getAgentEnsemble()->getLatestPortStats(rxPort);
      for (int i = 0; i < kNumPkts; i++) {
        sendPkt(payloadSize, txPort, mac);
      }

      // The frames reached rxPort over the link.
      HwPortStats after;
      WITH_RETRIES({
        after = getAgentEnsemble()->getLatestPortStats(rxPort);
        EXPECT_EVENTUALLY_GE(
            *after.inBytes_(),
            *before.inBytes_() +
                kNumPkts * (wireFrameSize(payloadSize) - kFcsSize));
      });

      auto dInPkts = *after.inUnicastPkts_() - *before.inUnicastPkts_();
      auto dInBytes = *after.inBytes_() - *before.inBytes_();
      auto dInDiscards = *after.inDiscardsRaw_() - *before.inDiscardsRaw_();
      // inUnicastPkts_ defaults to -1, so log absolutes alongside the deltas.
      XLOG(INFO) << "rxPort=" << rxPort << " payload=" << payloadSize
                 << " wireFrameSize=" << wireFrameSize(payloadSize)
                 << " dInUnicastPkts=" << dInPkts << " dInBytes=" << dInBytes
                 << " dInErrors=" << *after.inErrors_() - *before.inErrors_()
                 << " dInDiscards=" << dInDiscards << " | inUnicastPkts "
                 << *before.inUnicastPkts_() << "->" << *after.inUnicastPkts_()
                 << " inBytes " << *before.inBytes_() << "->"
                 << *after.inBytes_();

      ASSERT_LT(dInDiscards, kNumPkts)
          << "frames were discarded on ingress at wire frame size "
          << wireFrameSize(payloadSize)
          << "; this measures the drop path, not ingress accounting";

      EXPECT_GE(dInPkts, kNumPkts)
          << "ingress unicast counter did not advance for wire frame size "
          << wireFrameSize(payloadSize) << " (" << dInBytes
          << " ingress bytes were counted for the same frames)";
    }
  }
};

// Sized so a frame-size-dependent break in the counter is visible.
TEST_F(
    AgentEnsembleJumboFrameCounterTest,
    jumboFrameIngressUnicastPktsAcrossFrameSizes) {
  runIngressCounterTest(
      {1000, 1400, 1440, 1444, 1448, 1450, 1452, 1456, 1500, 2000});
}

} // namespace facebook::fboss
