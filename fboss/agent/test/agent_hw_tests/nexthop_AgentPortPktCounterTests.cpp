// (c) Nexthop Systems, Inc. and affiliates. Confidential and proprietary.

#include "fboss/agent/test/AgentHwTest.h"

#include "fboss/agent/packet/PktFactory.h"
#include "fboss/agent/test/ResourceLibUtil.h"
#include "fboss/agent/test/agent_hw_tests/AgentTestAddressConstants.h"
#include "fboss/agent/test/utils/CoppTestUtils.h"
#include "fboss/agent/test/utils/MultiPortTrafficTestUtils.h"

#include <folly/logging/xlog.h>

#include <chrono>
#include <thread>

namespace {
constexpr int kPayLoadLen{1000};
constexpr int kStatsWindowSeconds{10};
constexpr double kFrameSizeTolerance{0.20};
} // unnamed namespace

namespace facebook::fboss {

class AgentPortPktCounterTest : public AgentHwTest {
 public:
  std::vector<ProductionFeature> getProductionFeaturesVerified()
      const override {
    return {ProductionFeature::L3_FORWARDING, ProductionFeature::CPU_RX_TX};
  }

  // Counters can be correct on a subset of ports, so use them all.
  std::optional<size_t> maxRequiredInterfacePorts() const override {
    return std::nullopt;
  }

 protected:
  std::vector<PortID> portsUnderTest() const {
    return FLAGS_hyper_port ? masterLogicalHyperPortIds()
                            : masterLogicalInterfacePortIds();
  }

  void sendPacket(AgentEnsemble* ensemble, const folly::IPAddressV6& dstIp) {
    auto intfMac = getMacForFirstInterfaceWithPorts(getProgrammedState());
    auto srcMac = utility::MacAddressGenerator().get(intfMac.u64HBO() + 1);
    sendPacketSwitchedAsync(
        utility::makeUDPTxPacket(
            ensemble->getSw(),
            getVlanIDForTx(),
            srcMac,
            intfMac,
            folly::IPAddressV6(kTestSrcIpV6),
            dstIp,
            kTestSrcPort,
            kTestDstPort,
            0 /* dscp */,
            255 /* ttl */,
            std::vector<uint8_t>(kPayLoadLen, 0xff)));
  }
};

TEST_F(AgentPortPktCounterTest, VerifyRxPktCountersUnderTraffic) {
  auto setup = [this]() {
    auto config = getSw()->getConfig();
    utility::setTTLZeroCpuConfig(getAgentEnsemble()->getL3Asics(), config);
    applyNewConfig(config);
    utility::setupEcmpDataplaneLoopOnAllPorts(getAgentEnsemble());
  };
  auto verify = [this]() {
    auto ports = portsUnderTest();
    auto sendPacketFn =
        [this](AgentEnsemble* ensemble, const folly::IPAddressV6& dstIp) {
          sendPacket(ensemble, dstIp);
        };
    utility::createTrafficOnMultiplePorts(
        getAgentEnsemble(),
        static_cast<int>(ports.size()),
        sendPacketFn,
        10 /* desiredPct */);

    auto before = getNextUpdatedPortStats(ports);
    std::this_thread::sleep_for(std::chrono::seconds(kStatsWindowSeconds));
    auto after = getNextUpdatedPortStats(ports);

    for (auto portId : ports) {
      auto portName =
          getProgrammedState()->getPorts()->getNodeIf(portId)->getName();
      SCOPED_TRACE(
          folly::to<std::string>(
              "port ", portName, " (id ", static_cast<int>(portId), ")"));

      int64_t dInBytes = *after[portId].inBytes_() - *before[portId].inBytes_();
      int64_t dOutBytes =
          *after[portId].outBytes_() - *before[portId].outBytes_();
      int64_t dInUcast =
          *after[portId].inUnicastPkts_() - *before[portId].inUnicastPkts_();
      int64_t dOutUcast =
          *after[portId].outUnicastPkts_() - *before[portId].outUnicastPkts_();

      XLOG(DBG0) << portName << ": d_in_bytes=" << dInBytes
                 << " d_in_ucast=" << dInUcast << " d_out_bytes=" << dOutBytes
                 << " d_out_ucast=" << dOutUcast;

      EXPECT_GT(dInBytes, 0) << "dataplane loop not running";
      EXPECT_GT(dOutBytes, 0) << "dataplane loop not running";
      EXPECT_GT(dOutUcast, 0) << "dataplane loop not running";
      if (dInBytes <= 0 || dOutBytes <= 0 || dOutUcast <= 0) {
        continue;
      }

      EXPECT_GT(dInUcast, 0)
          << "in_unicast_pkts did not advance while in_bytes advanced by "
          << dInBytes;
      if (dInUcast <= 0) {
        continue;
      }

      // The port loops its own traffic back, so both directions carry the same
      // frames. Comparing the implied frame sizes catches a port whose packet
      // count covers more than that port.
      double outFrameSize = static_cast<double>(dOutBytes) / dOutUcast;
      double inFrameSize = static_cast<double>(dInBytes) / dInUcast;
      EXPECT_NEAR(inFrameSize, outFrameSize, outFrameSize * kFrameSizeTolerance)
          << "in_bytes/in_unicast_pkts (" << inFrameSize
          << ") disagrees with out_bytes/out_unicast_pkts (" << outFrameSize
          << "), off by a factor of " << (outFrameSize / inFrameSize);

      EXPECT_GE(*after[portId].inMulticastPkts_(), 0)
          << "in_multicast_pkts uninitialized";
      EXPECT_GE(*after[portId].inBroadcastPkts_(), 0)
          << "in_broadcast_pkts uninitialized";
    }
  };
  verifyAcrossWarmBoots(setup, verify);
}

} // namespace facebook::fboss
