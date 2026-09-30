/*
 *  Copyright (c) 2004-present, Facebook, Inc.
 *  All rights reserved.
 *
 *  This source code is licensed under the BSD-style license found in the
 *  LICENSE file in the root directory of this source tree. An additional grant
 *  of patent rights can be found in the PATENTS file in the same directory.
 *
 */
#include "fboss/agent/hw/sai/switch/SaiBridgeManager.h"
#include "fboss/agent/hw/sai/switch/SaiFdbManager.h"
#include "fboss/agent/hw/sai/switch/SaiPortManager.h"
#include "fboss/agent/hw/sai/switch/SaiVlanManager.h"
#include "fboss/agent/hw/sai/switch/tests/ManagerTestBase.h"
#include "fboss/agent/state/MacEntry.h"
#include "fboss/agent/state/MacTable.h"
#include "fboss/agent/state/Vlan.h"
#include "fboss/agent/types.h"

#include <gtest/gtest.h>

using namespace facebook::fboss;

class FdbManagerTest : public ManagerTestBase {
 public:
  void SetUp() override {
    setupStage = SetupStage::PORT | SetupStage::VLAN | SetupStage::INTERFACE;
    ManagerTestBase::SetUp();
    intf0 = testInterfaces[1];
  }

  void checkFdbEntry(sai_uint32_t metadata = 0) {
    auto vlanHandle = saiManagerTable->vlanManager().getVlanHandle(VlanID(0));
    auto vlanId = vlanHandle->vlan->adapterKey();
    SaiFdbTraits::FdbEntry entry{1, vlanId, kMac()};
    auto portHandle = saiManagerTable->portManager().getPortHandle(
        PortID(intf0.remoteHosts[0].id));
    auto expectedBridgePortId = portHandle->bridgePort->adapterKey();
    auto bridgePortId = saiApiTable->fdbApi().getAttribute(
        entry, SaiFdbTraits::Attributes::BridgePortId{});
    EXPECT_EQ(bridgePortId, expectedBridgePortId);
    EXPECT_EQ(
        saiApiTable->fdbApi().getAttribute(
            entry, SaiFdbTraits::Attributes::Metadata{}),
        metadata);
  }

  void addMacEntry(std::optional<sai_uint32_t> classId = std::nullopt) {
    updateOraAddMacEntry(kMac(), classId, false);
  }

  void updateMacEntry(std::optional<sai_uint32_t> classId = std::nullopt) {
    updateOraAddMacEntry(kMac(), classId, true);
  }

  void removeMacEntry() {
    auto newState = programmedState->clone();
    auto newMacTable = newState->getVlans()
                           ->getNode(VlanID(intf0.id))
                           ->getMacTable()
                           ->modify(VlanID(intf0.id), &newState);
    newMacTable->removeEntry(kMac());
    applyNewState(newState);
  }

  struct UnclaimedFdbEntries {
    SaiFdbTraits::FdbEntry dynamicEntry;
    SaiFdbTraits::FdbEntry staticEntry;
    sai_object_id_t bridgePortId{};
  };

  // Creates entries directly in the fake SAI, as a prior agent run would have
  // left them, and reloads them into the store as unclaimed warm boot handles.
  UnclaimedFdbEntries createUnclaimedFdbEntries() {
    auto vlanId = saiManagerTable->vlanManager()
                      .getVlanHandle(VlanID(0))
                      ->vlan->adapterKey();
    auto bridgePortId = static_cast<sai_object_id_t>(
        saiManagerTable->portManager()
            .getPortHandle(PortID(intf0.remoteHosts[0].id))
            ->bridgePort->adapterKey());
    SaiFdbTraits::FdbEntry dynamicEntry{
        1, vlanId, folly::MacAddress{"00:11:11:11:11:12"}};
    SaiFdbTraits::FdbEntry staticEntry{
        1, vlanId, folly::MacAddress{"00:11:11:11:11:13"}};
    saiApiTable->fdbApi().create<SaiFdbTraits>(
        dynamicEntry, {SAI_FDB_ENTRY_TYPE_DYNAMIC, bridgePortId, std::nullopt});
    saiApiTable->fdbApi().create<SaiFdbTraits>(
        staticEntry, {SAI_FDB_ENTRY_TYPE_STATIC, bridgePortId, std::nullopt});

    auto& fdbStore = saiStore->get<SaiFdbTraits>();
    EXPECT_EQ(fdbStore.size(), 0u);
    fdbStore.reload(nullptr, nullptr);
    // FakeSai always reports fdb Type as STATIC, so set it on the store object
    // only (skipHwWrite).
    fdbStore.get(dynamicEntry)
        ->setAttribute(
            SaiFdbTraits::Attributes::Type(SAI_FDB_ENTRY_TYPE_DYNAMIC), true);
    return {dynamicEntry, staticEntry, bridgePortId};
  }

  TestInterface intf0;

  static folly::MacAddress kMac() {
    return folly::MacAddress{"00:11:11:11:11:11"};
  }

 private:
  std::shared_ptr<MacEntry> makeMacEntry(
      folly::MacAddress mac,
      std::optional<sai_uint32_t> classId) {
    std::optional<cfg::AclLookupClass> metadata;
    if (classId) {
      metadata = static_cast<cfg::AclLookupClass>(classId.value());
    }
    return std::make_shared<MacEntry>(
        mac,
        PortDescriptor(PortID(intf0.remoteHosts[0].id)),
        std::optional<cfg::AclLookupClass>(metadata));
  }
  void updateOraAddMacEntry(
      folly::MacAddress mac,
      std::optional<sai_uint32_t> classId,
      bool update) {
    auto macEntry = makeMacEntry(mac, classId);
    auto newState = programmedState->clone();
    auto newMacTable = newState->getVlans()
                           ->getNode(VlanID(intf0.id))
                           ->getMacTable()
                           ->modify(VlanID(intf0.id), &newState);
    if (update) {
      newMacTable->updateEntry(
          macEntry->getMac(), macEntry->getPort(), macEntry->getClassID());
    } else {
      newMacTable->addEntry(macEntry);
    }
    applyNewState(newState);
  }
};

TEST_F(FdbManagerTest, addFdbEntry) {
  addMacEntry();
  checkFdbEntry();
}

TEST_F(FdbManagerTest, addFdbEntryWithMetdata) {
  addMacEntry(42);
  checkFdbEntry(42);
}

TEST_F(FdbManagerTest, addRemoveMetadata) {
  addMacEntry();
  checkFdbEntry();
  updateMacEntry(42);
  checkFdbEntry(42);
  updateMacEntry(std::nullopt);
  checkFdbEntry();
}

TEST_F(FdbManagerTest, doubleAddFdbEntry) {
  addMacEntry();
  EXPECT_THROW(addMacEntry(), FbossError);
}

TEST_F(FdbManagerTest, doubleRemoveFdbEntry) {
  addMacEntry();
  removeMacEntry();
  EXPECT_THROW(removeMacEntry(), FbossError);
}
TEST_F(FdbManagerTest, getL2EntriesTest) {
  addMacEntry();
  auto* fdbManager = &saiManagerTable->fdbManager();
  std::vector<L2EntryThrift> l2Entries = fdbManager->getL2Entries();
  ASSERT_FALSE(l2Entries.empty());

  bool found = false;
  for (const auto& entry : l2Entries) {
    if (*entry.mac() == kMac().toString()) {
      found = true;
      break;
    }
  }
  EXPECT_TRUE(found);
}

// With SOFTWARE learning an unclaimed dynamic entry must still be released,
// else checkUnexpectedUnclaimedWarmbootHandles() aborts the agent.
TEST_F(FdbManagerTest, removeUnclaimedDynamicEntriesSoftwareLearning) {
  saiManagerTable->bridgeManager().setL2LearningMode(
      cfg::L2LearningMode::SOFTWARE);
  auto [dynamicEntry, staticEntry, bridgePortId] = createUnclaimedFdbEntries();
  auto& fdbStore = saiStore->get<SaiFdbTraits>();
  ASSERT_TRUE(fdbStore.hasUnexpectedUnclaimedWarmbootHandles());

  saiManagerTable->fdbManager().removeUnclaimedDynanicEntries();

  EXPECT_EQ(fdbStore.get(dynamicEntry), nullptr);
  EXPECT_NE(fdbStore.get(staticEntry), nullptr);
  // The static entry is still unclaimed by switch state.
  EXPECT_TRUE(fdbStore.hasUnexpectedUnclaimedWarmbootHandles());
  // release() drops the store's handle but must not touch hardware.
  EXPECT_EQ(
      saiApiTable->fdbApi().getAttribute(
          dynamicEntry, SaiFdbTraits::Attributes::BridgePortId{}),
      bridgePortId);
}

TEST_F(FdbManagerTest, removeUnclaimedDynamicEntriesHardwareLearning) {
  saiManagerTable->bridgeManager().setL2LearningMode(
      cfg::L2LearningMode::HARDWARE);
  auto [dynamicEntry, staticEntry, bridgePortId] = createUnclaimedFdbEntries();
  auto& fdbStore = saiStore->get<SaiFdbTraits>();

  saiManagerTable->fdbManager().removeUnclaimedDynanicEntries();

  EXPECT_EQ(fdbStore.get(dynamicEntry), nullptr);
  EXPECT_NE(fdbStore.get(staticEntry), nullptr);
  EXPECT_EQ(
      saiApiTable->fdbApi().getAttribute(
          dynamicEntry, SaiFdbTraits::Attributes::BridgePortId{}),
      bridgePortId);
}
