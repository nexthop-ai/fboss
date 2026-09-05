/*
 *  Copyright (c) 2026-present, Nexthop Systems Inc
 *  All rights reserved.
 *
 *  This source code is licensed under the BSD-style license found in the
 *  LICENSE file in the root directory of this source tree. An additional grant
 *  of patent rights can be found in the PATENTS file in the same directory.
 *
 */

#include <folly/Conv.h>
#include <folly/ScopeGuard.h>

#include "fboss/agent/TxPacket.h"
#include "fboss/agent/hw/test/ConfigFactory.h"
#include "fboss/agent/packet/PktFactory.h"
#include "fboss/agent/test/AgentHwTest.h"
#include "fboss/agent/test/EcmpSetupHelper.h"
#include "fboss/agent/test/ResourceLibUtil.h"
#include "fboss/agent/test/TestUtils.h"
#include "fboss/agent/test/agent_hw_tests/AgentTestAddressConstants.h"
#include "fboss/agent/test/agent_hw_tests/AgentTestEcmpConstants.h"
#include "fboss/agent/test/utils/CoppTestUtils.h"
#include "fboss/agent/test/utils/OlympicTestUtils.h"
#include "fboss/agent/test/utils/PortTestUtils.h"
#include "fboss/lib/CommonUtils.h"

namespace facebook::fboss {

namespace {
constexpr int kUnicastQueue = 1;
constexpr uint8_t kUnicastQueueDscp = kUnicastQueue;
} // namespace

class AgentClearPortStatsTest : public AgentHwTest {
 protected:
  cfg::SwitchConfig initialConfig(
      const AgentEnsemble& ensemble) const override {
    auto cfg = utility::oneL3IntfConfig(
        ensemble.getSw()->getPlatformMapping(),
        ensemble.getL3Asics(),
        ensemble.masterLogicalPortIds()[0],
        ensemble.getSw()->getPlatformSupportsAddRemovePort());
    addQosMap(&cfg);
    addQueueConfig(&cfg, ensemble.getL3Asics());
    utility::addCpuQueueConfig(cfg, ensemble.getL3Asics(), ensemble.isSai());
    return cfg;
  }

  // Do not add PORT_TX_DISABLE: it is absent from some ASICs' production
  // feature lists, which silently drops this test from the run. The AQM tests
  // disable port TX the same way and declare only ECN/WRED.
  std::vector<ProductionFeature> getProductionFeaturesVerified()
      const override {
    return {ProductionFeature::L3_FORWARDING, ProductionFeature::L3_QOS};
  }

  PortID testPort() const {
    return masterLogicalPortIds()[0];
  }

  void setup() {
    utility::EcmpSetupAnyNPorts6 helper(
        getProgrammedState(), getSw()->needL2EntryForNeighbor(), dstMac());
    resolveNeighborAndProgramRoutes(helper, kDefaultEcmpWidth);
    // Park traffic in the MMU so the egress queues drop. TX stays disabled for
    // all of verify(): the port is in loopback with the route pointing back at
    // it, so draining would loop packets back in and keep generating drops.
    utility::setCreditWatchdogAndPortTx(getAgentEnsemble(), testPort(), false);
  }

  // New SDKs expect empty buffers at teardown; restore from a guard so a failed
  // assertion still re-enables TX.
  auto restorePortTxOnExit() {
    return folly::makeGuard([this]() {
      if (!FLAGS_setup_for_warmboot) {
        utility::setCreditWatchdogAndPortTx(
            getAgentEnsemble(), testPort(), true);
      }
    });
  }

  // Fill the MMU so the queues this traffic lands on accumulate egress drops.
  void generateEgressDrops(
      const std::function<std::unique_ptr<TxPacket>()>& pktFn) {
    auto mmuSizeBytes =
        checkSameAndGetAsicForTesting(getL3Asics())->getMMUSizeBytes();
    uint64_t bytesSent = 0;
    while (bytesSent < mmuSizeBytes + 20000) {
      auto pkt = pktFn();
      bytesSent += pkt->buf()->computeChainDataLength();
      sendPacketSwitchedAsync(std::move(pkt));
    }
    WITH_RETRIES({
      EXPECT_EVENTUALLY_GT(*getLatestPortStats(testPort()).outDiscards_(), 0);
    });
  }

  // Wait for the counter to stop moving before clearing, so a straggler drop
  // landing after the clear is not mistaken for a counter the clear skipped.
  int64_t waitForStableOutDiscards() {
    int64_t previous = -1;
    WITH_RETRIES({
      auto current = *getLatestPortStats(testPort()).outDiscards_();
      auto stable = current > 0 && current == previous;
      previous = current;
      EXPECT_EVENTUALLY_TRUE(stable);
    });
    return previous;
  }

  // -1 when absent rather than throwing: callers read this inside WITH_RETRIES,
  // where an exception aborts the test instead of retrying.
  static int64_t queueDiscards(const HwPortStats& stats, int queueId) {
    const auto& queueDiscardMap = *stats.queueOutDiscardPackets_();
    auto itr = queueDiscardMap.find(queueId);
    return itr == queueDiscardMap.end() ? -1 : itr->second;
  }

  bool multicastQueuesAreConfigured() const {
    auto streamTypes =
        utility::getStreamType(cfg::PortType::INTERFACE_PORT, getL3Asics());
    return streamTypes.find(cfg::StreamType::MULTICAST) != streamTypes.end();
  }

  std::unique_ptr<TxPacket> createUnicastPkt() const {
    return createPkt(dstMac(), kUnicastQueueDscp);
  }

  // L2 broadcast floods in the VLAN and egresses on a multicast queue.
  std::unique_ptr<TxPacket> createBroadcastPkt() const {
    return createPkt(folly::MacAddress("ff:ff:ff:ff:ff:ff"), 0);
  }

 private:
  MacAddress dstMac() const {
    return getMacForFirstInterfaceWithPortsForTesting(getProgrammedState());
  }

  std::unique_ptr<TxPacket> createPkt(folly::MacAddress dst, uint8_t dscpVal)
      const {
    auto srcMac = utility::MacAddressGenerator().get(dstMac().u64HBO() + 1);
    return utility::makeUDPTxPacket(
        getSw(),
        getVlanIDForTx(),
        srcMac,
        dst,
        folly::IPAddressV6(kTestSrcIpV6),
        folly::IPAddressV6(kTestDstIpV6),
        kTestSrcPort,
        kTestDstPort,
        // Trailing 2 bits are for ECN
        static_cast<uint8_t>(dscpVal << 2),
        255, // hop limit
        std::vector<uint8_t>(7000, 0xff));
  }

  // dscp N -> traffic class N -> queue N. All other dscps land on queue 0 so
  // background traffic does not muddy the per queue counters under assert.
  void addQosMap(cfg::SwitchConfig* cfg) const {
    cfg::QosMap qosMap;
    std::map<int, std::vector<uint8_t>> queue2Dscp = {
        {0, {0}},
        {kUnicastQueue, {kUnicastQueueDscp}},
    };
    for (auto dscp = 1; dscp < 64; ++dscp) {
      if (dscp != kUnicastQueueDscp) {
        queue2Dscp[0].push_back(dscp);
      }
    }
    qosMap.dscpMaps()->resize(queue2Dscp.size());
    ssize_t qosMapIdx = 0;
    for (const auto& [queue, dscps] : queue2Dscp) {
      qosMap.dscpMaps()[qosMapIdx].internalTrafficClass() = queue;
      for (auto dscp : dscps) {
        qosMap.dscpMaps()[qosMapIdx].fromDscpToTrafficClass()->push_back(dscp);
      }
      qosMap.trafficClassToQueueId()->emplace(queue, queue);
      ++qosMapIdx;
    }
    cfg->qosPolicies()->resize(1);
    cfg->qosPolicies()[0].name() = "qp";
    cfg->qosPolicies()[0].qosMap() = qosMap;

    cfg::TrafficPolicyConfig dataPlaneTrafficPolicy;
    dataPlaneTrafficPolicy.defaultQosPolicy() = "qp";
    cfg->dataPlaneTrafficPolicy() = dataPlaneTrafficPolicy;
    cfg::CPUTrafficPolicyConfig cpuConfig;
    cfg::TrafficPolicyConfig cpuTrafficPolicy;
    cpuTrafficPolicy.defaultQosPolicy() = "qp";
    cpuConfig.trafficPolicy() = cpuTrafficPolicy;
    cfg->cpuTrafficPolicy() = cpuConfig;
  }

  void addQueueConfig(
      cfg::SwitchConfig* config,
      const std::vector<const HwAsic*>& asics) const {
    auto streamType =
        *(utility::getStreamType(cfg::PortType::INTERFACE_PORT, asics).begin());
    std::vector<cfg::PortQueue> portQueues;
    for (auto queueId : {0, kUnicastQueue}) {
      cfg::PortQueue queue;
      queue.id() = queueId;
      queue.name() = folly::to<std::string>("queue", queueId);
      queue.streamType() = streamType;
      queue.scheduling() = cfg::QueueScheduling::WEIGHTED_ROUND_ROBIN;
      queue.weight() = 1;
      portQueues.push_back(queue);
    }
    config->portQueueConfigs()["queue_config"] = portQueues;
    for (auto& port : *config->ports()) {
      port.portQueueConfigName() = "queue_config";
    }
  }
};

// Drops on a unicast queue, which is always in the port queue config and so
// always in the clear path.
TEST_F(AgentClearPortStatsTest, clearOutDiscardsOnUnicastQueue) {
  auto verify = [this]() {
    auto restoreTx = restorePortTxOnExit();
    generateEgressDrops([this]() { return createUnicastPkt(); });
    auto outDiscardsBeforeClear = waitForStableOutDiscards();
    auto statsBeforeClear = getLatestPortStats(testPort());
    auto queueDiscardsBeforeClear =
        queueDiscards(statsBeforeClear, kUnicastQueue);
    XLOG(INFO) << "Before clear: port outDiscards=" << outDiscardsBeforeClear
               << " outCongestionDiscards="
               << *statsBeforeClear.outCongestionDiscardPkts_() << " queue"
               << kUnicastQueue << " discards=" << queueDiscardsBeforeClear;
    ASSERT_GT(queueDiscardsBeforeClear, 0)
        << "traffic did not land on queue " << kUnicastQueue
        << ", the qos map is not steering as this test assumes";

    getAgentEnsemble()->clearPortStats();

    WITH_RETRIES({
      auto stats = getLatestPortStats(testPort());
      XLOG(INFO) << "After clear: port outDiscards=" << *stats.outDiscards_()
                 << " queue" << kUnicastQueue
                 << " discards=" << queueDiscards(stats, kUnicastQueue);
      EXPECT_EVENTUALLY_EQ(queueDiscards(stats, kUnicastQueue), 0);
      EXPECT_EVENTUALLY_EQ(*stats.outDiscards_(), 0);
    });
  };
  verifyAcrossWarmBoots([this]() { setup(); }, verify);
}

// Drops on a multicast queue, which the port queue config does not describe on
// XGS. outDiscards_ is a port level counter that includes them, so it must
// still return to zero after a clear.
TEST_F(AgentClearPortStatsTest, clearOutDiscardsOnMulticastQueue) {
  if (multicastQueuesAreConfigured()) {
    GTEST_SKIP() << "ASIC configures multicast queues for interface ports, so "
                    "they are in configuredQueues and this gap cannot occur";
  }
  auto verify = [this]() {
    auto restoreTx = restorePortTxOnExit();
    generateEgressDrops([this]() { return createBroadcastPkt(); });
    auto outDiscardsBeforeClear = waitForStableOutDiscards();
    auto statsBeforeClear = getLatestPortStats(testPort());
    auto congestionDiscardsBeforeClear =
        *statsBeforeClear.outCongestionDiscardPkts_();
    XLOG(INFO) << "Before clear: port outDiscards=" << outDiscardsBeforeClear
               << " outCongestionDiscards=" << congestionDiscardsBeforeClear;

    // Multicast queue drops are counted at the port and nowhere else. If this
    // moved, the traffic landed on a unicast queue instead.
    ASSERT_EQ(congestionDiscardsBeforeClear, 0)
        << "flooded traffic dropped on a unicast queue; expected the drops to "
           "be invisible to the per queue counters";

    getAgentEnsemble()->clearPortStats();

    WITH_RETRIES({
      auto stats = getLatestPortStats(testPort());
      XLOG(INFO) << "After clear: port outDiscards=" << *stats.outDiscards_()
                 << " outCongestionDiscards="
                 << *stats.outCongestionDiscardPkts_();
      EXPECT_EVENTUALLY_EQ(*stats.outDiscards_(), 0);
    });
  };
  verifyAcrossWarmBoots([this]() { setup(); }, verify);
}

} // namespace facebook::fboss
