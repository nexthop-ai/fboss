/*
 *  Copyright (c) 2026, Nexthop Systems Inc
 *  All rights reserved.
 *
 *  This source code is licensed under the BSD-style license found in the
 *  LICENSE file in the root directory of this source tree. An additional grant
 *  of patent rights can be found in the PATENTS file in the same directory.
 */
#include "cfboss/dataplane/VethPacketBackend.h"

#include "cfboss/dataplane/PortMap.h"

#include <folly/json.h>

#include <gtest/gtest.h>

#include <sys/socket.h>
#include <unistd.h>

#include <atomic>
#include <chrono>
#include <map>
#include <memory>
#include <mutex>
#include <set>
#include <stdexcept>
#include <string>
#include <thread>
#include <utility>
#include <vector>

namespace facebook::fboss {
namespace {

// Test seam: each veth gets one socketpair end as its packet fd (no privilege
// or real interfaces); the retained peer end lets tests inject RX frames.
class FakeVethSyscalls : public VethSyscalls {
 public:
  ~FakeVethSyscalls() override {
    for (int fd : peerFds_) {
      ::close(fd);
    }
  }

  // Owns the peer fds; non-copyable/movable (constructed only via make_shared).
  FakeVethSyscalls() = default;
  FakeVethSyscalls(const FakeVethSyscalls&) = delete;
  FakeVethSyscalls& operator=(const FakeVethSyscalls&) = delete;
  FakeVethSyscalls(FakeVethSyscalls&&) = delete;
  FakeVethSyscalls& operator=(FakeVethSyscalls&&) = delete;

  std::pair<int, int> openPacketSocket(const std::string& ifname) override {
    int fds[2] = {-1, -1};
    if (::socketpair(AF_UNIX, SOCK_DGRAM, 0, fds) != 0) {
      throw std::runtime_error("FakeVethSyscalls: socketpair failed");
    }
    // Retain the peer end so the returned fd never HUPs.
    peerFds_.push_back(fds[1]);
    ++openCalls;
    openedIfNames.push_back(ifname);
    return {fds[0], kBaseIfindex + openCalls};
  }

  uint64_t readInterfaceStat(const std::string& veth, const std::string& stat)
      override {
    auto it = stats.find(stat);
    return it == stats.end() ? 0 : it->second;
  }

  // Peer end of the i-th opened veth; write here to inject an RX frame.
  int peerFd(size_t i) const {
    return peerFds_.at(i);
  }

  static constexpr int kBaseIfindex = 1000;
  int openCalls{0};
  std::vector<std::string> openedIfNames;
  std::map<std::string, uint64_t> stats;

 private:
  std::vector<int> peerFds_;
};

// The SAI packet callback is a plain function pointer (cannot capture), so RX
// observations are recorded through these globals.
std::atomic<int> gRxCount{0};
std::atomic<int> gInCallback{0};
std::atomic<bool> gOverlap{false};
std::mutex gSeenOidsMutex;
std::set<sai_object_id_t> gSeenOids;

void rxRecordCallback(
    sai_object_id_t /*switch_id*/,
    sai_size_t /*buffer_size*/,
    const void* /*buffer*/,
    uint32_t attr_count,
    const sai_attribute_t* attr_list) {
  if (gInCallback.fetch_add(1) != 0) {
    gOverlap = true; // a second RX thread entered the callback concurrently
  }
  for (uint32_t i = 0; i < attr_count; ++i) {
    if (attr_list[i].id == SAI_HOSTIF_PACKET_ATTR_INGRESS_PORT) {
      std::lock_guard<std::mutex> g(gSeenOidsMutex);
      gSeenOids.insert(attr_list[i].value.oid);
    }
  }
  // Hold the callback briefly so any unserialized concurrent delivery is seen.
  std::this_thread::sleep_for(std::chrono::milliseconds(1));
  gInCallback.fetch_sub(1);
  gRxCount.fetch_add(1);
}

std::shared_ptr<const cfboss::PortMap> makePortMap(const std::string& json) {
  return std::make_shared<const cfboss::PortMap>(
      cfboss::PortMap::parse(folly::parseJson(json)));
}

constexpr auto kTwoPortMap = R"({
  "ports": [
    {"lane": 1, "veth": "fboss_p1"},
    {"lane": 2, "veth": "fboss_p2"}
  ]
})";

TEST(VethPacketBackendTest, opensSocketPerVethThroughSeam) {
  auto syscalls = std::make_shared<FakeVethSyscalls>();
  VethPacketBackend backend(makePortMap(kTwoPortMap), syscalls);
  EXPECT_EQ(syscalls->openCalls, 2);
  EXPECT_EQ(
      syscalls->openedIfNames,
      (std::vector<std::string>{"fboss_p1", "fboss_p2"}));
}

TEST(VethPacketBackendTest, portStatsReadThroughSysfsSeam) {
  auto syscalls = std::make_shared<FakeVethSyscalls>();
  syscalls->stats = {
      {"rx_bytes", 4096},
      {"rx_packets", 100},
      {"multicast", 30},
      {"tx_bytes", 2048},
      {"tx_packets", 50},
  };
  VethPacketBackend backend(makePortMap(kTwoPortMap), syscalls);

  constexpr sai_object_id_t kOid = 0x1000;
  backend.onPortCreated(kOid, {1});

  const std::vector<sai_stat_id_t> ids = {
      SAI_PORT_STAT_IF_IN_OCTETS,
      SAI_PORT_STAT_IF_IN_UCAST_PKTS,
      SAI_PORT_STAT_IF_IN_MULTICAST_PKTS,
      SAI_PORT_STAT_IF_OUT_OCTETS,
      SAI_PORT_STAT_IF_OUT_UCAST_PKTS,
  };
  std::vector<uint64_t> counters(ids.size(), 0);
  EXPECT_EQ(
      backend.getPortStats(
          kOid, static_cast<uint32_t>(ids.size()), ids.data(), counters.data()),
      SAI_STATUS_SUCCESS);

  EXPECT_EQ(counters[0], 4096u); // in octets = rx_bytes
  EXPECT_EQ(counters[1], 70u); // in ucast   = rx_packets - multicast
  EXPECT_EQ(counters[2], 30u); // in mcast   = multicast
  EXPECT_EQ(counters[3], 2048u); // out octets = tx_bytes
  EXPECT_EQ(counters[4], 50u); // out ucast   = tx_packets
}

// Writes to both peer ends drive both RX threads concurrently; assert every
// frame arrives with its ingress OID and that deliveries are serialized.
TEST(VethPacketBackendTest, concurrentRxDeliversSerializedWithIngressPort) {
  gRxCount = 0;
  gInCallback = 0;
  gOverlap = false;
  {
    std::lock_guard<std::mutex> g(gSeenOidsMutex);
    gSeenOids.clear();
  }

  auto syscalls = std::make_shared<FakeVethSyscalls>();
  VethPacketBackend backend(makePortMap(kTwoPortMap), syscalls);
  constexpr sai_object_id_t kOid1 = 0x1001;
  constexpr sai_object_id_t kOid2 = 0x1002;
  backend.onPortCreated(kOid1, {1});
  backend.onPortCreated(kOid2, {2});
  backend.setRxCallback(/*switch_id=*/0x7, &rxRecordCallback);

  constexpr int kFramesPerVeth = 50;
  const std::vector<uint8_t> frame(64, 0xab);
  for (int i = 0; i < kFramesPerVeth; ++i) {
    ASSERT_EQ(
        ::write(syscalls->peerFd(0), frame.data(), frame.size()),
        static_cast<ssize_t>(frame.size()));
    ASSERT_EQ(
        ::write(syscalls->peerFd(1), frame.data(), frame.size()),
        static_cast<ssize_t>(frame.size()));
  }

  constexpr int kExpected = 2 * kFramesPerVeth;
  for (int i = 0; i < 500 && gRxCount.load() < kExpected; ++i) {
    std::this_thread::sleep_for(std::chrono::milliseconds(10));
  }
  EXPECT_EQ(gRxCount.load(), kExpected);
  EXPECT_FALSE(gOverlap.load());
  std::lock_guard<std::mutex> g(gSeenOidsMutex);
  EXPECT_EQ(gSeenOids, (std::set<sai_object_id_t>{kOid1, kOid2}));
}

TEST(VethPacketBackendTest, portStatsUnknownOidReturnsZeros) {
  auto syscalls = std::make_shared<FakeVethSyscalls>();
  syscalls->stats = {{"rx_bytes", 999}};
  VethPacketBackend backend(makePortMap(kTwoPortMap), syscalls);

  const std::vector<sai_stat_id_t> ids = {SAI_PORT_STAT_IF_IN_OCTETS};
  std::vector<uint64_t> counters(ids.size(), 123);
  EXPECT_EQ(
      backend.getPortStats(
          0xdead,
          static_cast<uint32_t>(ids.size()),
          ids.data(),
          counters.data()),
      SAI_STATUS_SUCCESS);
  EXPECT_EQ(counters[0], 0u);
}

} // namespace
} // namespace facebook::fboss
