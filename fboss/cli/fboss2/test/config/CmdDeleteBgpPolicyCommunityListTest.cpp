// (c) Meta Platforms, Inc. and affiliates. Confidential and proprietary.

<<<<<<< HEAD
#include <configerator/structs/neteng/fboss/bgp/gen-cpp2/bgp_config_types.h>
#include <gmock/gmock.h>
#include <gtest/gtest.h>

#include <filesystem>
#include <stdexcept>
#include <string>
#include <vector>

#include "configerator/structs/neteng/bgp_policy/thrift/gen-cpp2/bgp_policy_types.h"
#include "fboss/cli/fboss2/commands/config/protocol/bgp/policy/community-list/BgpCommunityListCliUtils.h"
#include "fboss/cli/fboss2/commands/config/protocol/bgp/policy/community-list/CmdConfigProtocolBgpPolicyCommunityList.h"
#include "fboss/cli/fboss2/commands/delete/protocol/bgp/policy/community-list/CmdDeleteProtocolBgpPolicyCommunityList.h"
#include "fboss/cli/fboss2/session/ConfigSession.h"
#include "fboss/cli/fboss2/test/config/CmdConfigTestBase.h"
#include "fboss/cli/fboss2/utils/HostInfo.h"

using namespace ::testing;

namespace facebook::fboss {

// Deleting only touches the BGP side of ConfigSession, which seeds from thrift
// schema defaults when neither a staged session nor a system bgpcpp.conf
// exists — so no seed agent config is needed (mirrors
// CmdDeleteBgpPolicyAsPathListTest).
class CmdDeleteBgpPolicyCommunityListTestFixture : public CmdConfigTestBase {
 public:
  CmdDeleteBgpPolicyCommunityListTestFixture()
      : CmdConfigTestBase("bgp_community_list_delete_test_%%%%-%%%%-%%%%", "") {
  }

  void SetUp() override {
    CmdConfigTestBase::SetUp();
    setupTestableConfigSession();
  }

  std::string configure(const std::vector<std::string>& tokens) {
    CmdConfigProtocolBgpPolicyCommunityList cmd;
    HostInfo hostInfo("testhost");
    return cmd.queryClient(hostInfo, BgpCommunityListConfig(tokens));
  }

  // Seed an inline Community member. The member level is its own subcommand
  // (CmdConfigProtocolBgpPolicyCommunityListCommunity), which lands above this
  // command in the stack — so stage it through the shared helpers rather than
  // depending on that handler.
  void configureCommunity(
      const std::string& listName,
      const std::string& communityName,
      const std::string& value) {
    auto& session = ConfigSession::getInstance();
    auto& list =
        bgpcli::findOrCreateCommunityList(session.getBgpConfig(), listName);
    bgpcli::findOrCreateCommunityMember(list, communityName).value() = value;
    session.saveBgpConfig();
  }

  std::string del(const std::vector<std::string>& tokens) {
    CmdDeleteProtocolBgpPolicyCommunityList cmd;
    HostInfo hostInfo("testhost");
    return cmd.queryClient(hostInfo, BgpCommunityListRef(tokens));
  }

  const std::vector<bgp::bgp_policy::CommunityList>& lists() {
    return *ConfigSession::getInstance()
                .getBgpConfig()
                .policies()
                .ensure()
                .community_lists();
  }

  bool sessionFileExists() {
    return std::filesystem::exists(
        ConfigSession::getInstance().getBgpSessionConfigPath());
  }
};

// ==============================================================================
// BgpCommunityListRef (arg) validation
// ==============================================================================

TEST_F(CmdDeleteBgpPolicyCommunityListTestFixture, argValidation) {
  auto listOnly = BgpCommunityListRef({"CL100"});
  EXPECT_EQ(listOnly.listName(), "CL100");
  EXPECT_FALSE(listOnly.hasCommunity());

  auto withMember = BgpCommunityListRef({"CL100", "community", "CM1"});
  EXPECT_EQ(withMember.listName(), "CL100");
  EXPECT_TRUE(withMember.hasCommunity());
  EXPECT_EQ(withMember.communityName(), "CM1");

  // Invalid: empty, empty names, non-`community` second token, missing
  // community name, extra tokens.
  EXPECT_THROW(BgpCommunityListRef({}), std::invalid_argument);
  EXPECT_THROW(BgpCommunityListRef({""}), std::invalid_argument);
  EXPECT_THROW(BgpCommunityListRef({"CL100", "CL200"}), std::invalid_argument);
  EXPECT_THROW(
      BgpCommunityListRef({"CL100", "community"}), std::invalid_argument);
  EXPECT_THROW(
      BgpCommunityListRef({"CL100", "community", ""}), std::invalid_argument);
  EXPECT_THROW(
      BgpCommunityListRef({"CL100", "community", "CM1", "extra"}),
      std::invalid_argument);
}

// ==============================================================================
// queryClient
// ==============================================================================

TEST_F(CmdDeleteBgpPolicyCommunityListTestFixture, deleteExistingList) {
  configureCommunity("CL100", "CM1", "65000:100");
  configure({"CL200", "description", "keep"});
  ASSERT_EQ(lists().size(), 2);

  auto result = del({"CL100"});
  EXPECT_THAT(
      result, HasSubstr("Successfully deleted BGP community-list CL100"));
  // The other list survives untouched.
  ASSERT_EQ(lists().size(), 1);
  EXPECT_EQ(*lists()[0].name(), "CL200");
  EXPECT_EQ(*lists()[0].description(), "keep");
  EXPECT_TRUE(sessionFileExists());
}

TEST_F(CmdDeleteBgpPolicyCommunityListTestFixture, deleteUnknownListRejected) {
  auto result = del({"NO-SUCH-LIST"});
  EXPECT_THAT(
      result, HasSubstr("Error: BGP community-list NO-SUCH-LIST not found"));
  // Nothing was persisted for the failed delete.
  EXPECT_FALSE(sessionFileExists())
      << "session file should not exist after rejected delete";
}

TEST_F(
    CmdDeleteBgpPolicyCommunityListTestFixture,
    deleteUnknownLeavesOthersIntact) {
  configure({"CL100", "description", "one"});
  auto result = del({"CL200"});
  EXPECT_THAT(result, HasSubstr("not found"));
  ASSERT_EQ(lists().size(), 1);
  EXPECT_EQ(*lists()[0].name(), "CL100");
}

// ==============================================================================
// queryClient: single community member deletion
// ==============================================================================

TEST_F(CmdDeleteBgpPolicyCommunityListTestFixture, deleteExistingCommunity) {
  configureCommunity("CL100", "CM1", "65000:100");
  configureCommunity("CL100", "CM2", "65000:200");

  auto result = del({"CL100", "community", "CM1"});
  EXPECT_THAT(
      result,
      HasSubstr("Successfully deleted BGP community-list CL100 community CM1"));
  // The list and its other member survive.
  ASSERT_EQ(lists().size(), 1);
  ASSERT_TRUE(lists()[0].members().has_value());
  ASSERT_EQ(lists()[0].members()->size(), 1);
  EXPECT_EQ(*(*lists()[0].members())[0].community_ref()->name(), "CM2");
  EXPECT_TRUE(sessionFileExists());
}

TEST_F(
    CmdDeleteBgpPolicyCommunityListTestFixture,
    deleteLastCommunityUnsetsMembers) {
  configureCommunity("CL100", "CM1", "65000:100");

  auto result = del({"CL100", "community", "CM1"});
  EXPECT_THAT(result, HasSubstr("Successfully deleted"));
  // The list stays, shaped like one that never had members.
  ASSERT_EQ(lists().size(), 1);
  EXPECT_EQ(*lists()[0].name(), "CL100");
  EXPECT_FALSE(lists()[0].members().has_value());
}

TEST_F(
    CmdDeleteBgpPolicyCommunityListTestFixture,
    deleteUnknownCommunityRejected) {
  configureCommunity("CL100", "CM1", "65000:100");
  // Consume the session file created by configure so we can assert the
  // rejected delete does not persist anything new.
  ASSERT_TRUE(sessionFileExists());

  auto result = del({"CL100", "community", "NO-SUCH-COMMUNITY"});
  EXPECT_THAT(
      result,
      HasSubstr(
          "Error: BGP community-list CL100 community NO-SUCH-COMMUNITY not "
          "found"));
  // The existing member is untouched.
  ASSERT_EQ(lists().size(), 1);
  ASSERT_TRUE(lists()[0].members().has_value());
  ASSERT_EQ(lists()[0].members()->size(), 1);
  EXPECT_EQ(*(*lists()[0].members())[0].community_ref()->name(), "CM1");
}

TEST_F(
    CmdDeleteBgpPolicyCommunityListTestFixture,
    deleteCommunityFromMemberlessListRejected) {
  configure({"CL100", "description", "no", "members"});

  auto result = del({"CL100", "community", "CM1"});
  EXPECT_THAT(
      result,
      HasSubstr("Error: BGP community-list CL100 community CM1 not found"));
  ASSERT_EQ(lists().size(), 1);
  EXPECT_FALSE(lists()[0].members().has_value());
}

TEST_F(
    CmdDeleteBgpPolicyCommunityListTestFixture,
    deleteCommunityFromUnknownListRejected) {
  auto result = del({"NO-SUCH-LIST", "community", "CM1"});
  EXPECT_THAT(
      result, HasSubstr("Error: BGP community-list NO-SUCH-LIST not found"));
  EXPECT_FALSE(sessionFileExists())
      << "session file should not exist after rejected delete";
||||||| c31f2b21c7
=======
#include <gmock/gmock.h>
#include <gtest/gtest.h>

#include <filesystem>
#include <stdexcept>
#include <string>
#include <vector>

#include "fboss/cli/fboss2/commands/config/protocol/bgp/policy/community-list/CmdConfigProtocolBgpPolicyCommunityList.h"
#include "fboss/cli/fboss2/commands/delete/protocol/bgp/policy/community-list/CmdDeleteProtocolBgpPolicyCommunityList.h"
#include "fboss/cli/fboss2/session/ConfigSession.h"
#include "fboss/cli/fboss2/test/config/CmdConfigTestBase.h"
#include "fboss/cli/fboss2/utils/HostInfo.h"

#ifndef IS_OSS
#include <configerator/structs/neteng/bgp_policy/thrift/gen-cpp2/bgp_policy_types.h>
#include <configerator/structs/neteng/fboss/bgp/gen-cpp2/bgp_config_types.h>
#else
#include <neteng/fboss/bgp/public_tld/configerator/structs/neteng/fboss/bgp/gen-cpp2/bgp_config_types.h>
#endif

using namespace ::testing;

namespace facebook::fboss {

// Deleting only touches the BGP side of ConfigSession, which seeds from thrift
// schema defaults when neither a staged session nor a system bgpcpp.conf
// exists — so no seed agent config is needed (mirrors
// CmdDeleteBgpPolicyAsPathListTest).
class CmdDeleteBgpPolicyCommunityListTestFixture : public CmdConfigTestBase {
 public:
  CmdDeleteBgpPolicyCommunityListTestFixture()
      : CmdConfigTestBase("bgp_community_list_delete_test_%%%%-%%%%-%%%%", "") {
  }

  void SetUp() override {
    CmdConfigTestBase::SetUp();
    setupTestableConfigSession();
  }

  std::string configure(const std::vector<std::string>& tokens) {
    CmdConfigProtocolBgpPolicyCommunityList cmd;
    HostInfo hostInfo("testhost");
    return cmd.queryClient(hostInfo, BgpCommunityListConfig(tokens));
  }

  std::string del(const std::vector<std::string>& tokens) {
    CmdDeleteProtocolBgpPolicyCommunityList cmd;
    HostInfo hostInfo("testhost");
    return cmd.queryClient(hostInfo, BgpCommunityListRef(tokens));
  }

  const std::vector<bgp::bgp_policy::CommunityList>& lists() {
    return *ConfigSession::getInstance()
                .getBgpConfig()
                .policies()
                .ensure()
                .community_lists();
  }

  bool sessionFileExists() {
    return std::filesystem::exists(
        ConfigSession::getInstance().getBgpSessionConfigPath());
  }
};

// ==============================================================================
// BgpCommunityListRef (arg) validation
// ==============================================================================

TEST_F(CmdDeleteBgpPolicyCommunityListTestFixture, argValidation) {
  auto listOnly = BgpCommunityListRef({"CL100"});
  EXPECT_EQ(listOnly.listName(), "CL100");
  EXPECT_FALSE(listOnly.hasCommunity());

  // Optional `community <community>` selector.
  auto withValue = BgpCommunityListRef({"CL100", "community", "65000:100"});
  EXPECT_EQ(withValue.listName(), "CL100");
  EXPECT_TRUE(withValue.hasCommunity());
  EXPECT_EQ(withValue.community(), "65000:100");

  // Invalid: empty, empty name, extra tokens, incomplete or trailing selector.
  EXPECT_THROW(BgpCommunityListRef({}), std::invalid_argument);
  EXPECT_THROW(BgpCommunityListRef({""}), std::invalid_argument);
  EXPECT_THROW(BgpCommunityListRef({"CL100", "CL200"}), std::invalid_argument);
  EXPECT_THROW(
      BgpCommunityListRef({"CL100", "community"}), std::invalid_argument);
  EXPECT_THROW(
      BgpCommunityListRef({"CL100", "community", ""}), std::invalid_argument);
  EXPECT_THROW(
      BgpCommunityListRef({"CL100", "community", "65000:100", "extra"}),
      std::invalid_argument);
}

// ==============================================================================
// queryClient
// ==============================================================================

TEST_F(CmdDeleteBgpPolicyCommunityListTestFixture, deleteExistingList) {
  configure({"CL100", "community", "65000:100"});
  configure({"CL200", "description", "keep"});
  ASSERT_EQ(lists().size(), 2);

  auto result = del({"CL100"});
  EXPECT_THAT(
      result, HasSubstr("Successfully deleted BGP community-list CL100"));
  // The other list survives untouched.
  ASSERT_EQ(lists().size(), 1);
  EXPECT_EQ(*lists()[0].name(), "CL200");
  EXPECT_EQ(*lists()[0].description(), "keep");
  EXPECT_TRUE(sessionFileExists());
}

// Delete mirrors add: an absent target is a success with a warning, never an
// error, so a replayed script stays idempotent.
TEST_F(CmdDeleteBgpPolicyCommunityListTestFixture, deleteUnknownListWarns) {
  auto result = del({"NO-SUCH-LIST"});
  EXPECT_THAT(
      result,
      HasSubstr(
          "Warning: BGP community-list NO-SUCH-LIST does not exist; nothing "
          "to delete"));
  EXPECT_THAT(result, Not(HasSubstr("Error:")));
  // Nothing changed, so nothing is staged.
  EXPECT_FALSE(sessionFileExists())
      << "session file should not exist after a no-op delete";
}

TEST_F(CmdDeleteBgpPolicyCommunityListTestFixture, deleteTwiceIsIdempotent) {
  configure({"CL100", "description", "delete-me"});
  EXPECT_THAT(del({"CL100"}), HasSubstr("Successfully deleted"));
  EXPECT_TRUE(lists().empty());

  auto again = del({"CL100"});
  EXPECT_THAT(
      again,
      HasSubstr(
          "Warning: BGP community-list CL100 does not exist; nothing to "
          "delete"));
  EXPECT_THAT(again, Not(HasSubstr("Error:")));
  EXPECT_TRUE(lists().empty());
}

TEST_F(
    CmdDeleteBgpPolicyCommunityListTestFixture,
    deleteUnknownLeavesOthersIntact) {
  configure({"CL100", "description", "one"});
  auto result = del({"CL200"});
  EXPECT_THAT(result, HasSubstr("does not exist"));
  ASSERT_EQ(lists().size(), 1);
  EXPECT_EQ(*lists()[0].name(), "CL100");
}

// ==============================================================================
// community selector — remove one value, keep the list
// ==============================================================================

TEST_F(CmdDeleteBgpPolicyCommunityListTestFixture, deleteOneCommunity) {
  configure({"CL100", "community", "65000:100"});
  configure({"CL100", "community", "65000:200"});

  auto result = del({"CL100", "community", "65000:100"});
  EXPECT_THAT(
      result,
      HasSubstr(
          "Successfully deleted BGP community-list CL100 community "
          "65000:100"));
  // The list and its other value survive.
  ASSERT_EQ(lists().size(), 1);
  EXPECT_EQ(*lists()[0].communities(), std::vector<std::string>({"65000:200"}));
  EXPECT_TRUE(sessionFileExists());

  // Deleting the last value clears communities but keeps the list.
  del({"CL100", "community", "65000:200"});
  ASSERT_EQ(lists().size(), 1);
  EXPECT_EQ(*lists()[0].name(), "CL100");
  EXPECT_FALSE(lists()[0].communities().has_value());
}

TEST_F(
    CmdDeleteBgpPolicyCommunityListTestFixture,
    deleteUnknownCommunityWarns) {
  configure({"CL100", "community", "65000:100"});
  // Remove the session file created by configure so its absence afterwards
  // proves the no-op delete did not persist anything new.
  ASSERT_TRUE(sessionFileExists());
  std::filesystem::remove(
      ConfigSession::getInstance().getBgpSessionConfigPath());

  auto result = del({"CL100", "community", "65000:999"});
  EXPECT_THAT(
      result,
      HasSubstr(
          "Warning: BGP community-list CL100 has no community 65000:999; "
          "nothing to delete"));
  EXPECT_THAT(result, Not(HasSubstr("Error:")));
  EXPECT_FALSE(sessionFileExists())
      << "no-op delete must not persist a session file";
  // The existing value is untouched.
  ASSERT_EQ(lists().size(), 1);
  EXPECT_EQ(*lists()[0].communities(), std::vector<std::string>({"65000:100"}));
}

TEST_F(
    CmdDeleteBgpPolicyCommunityListTestFixture,
    deleteCommunityTwiceIsIdempotent) {
  configure({"CL100", "community", "65000:100"});
  EXPECT_THAT(
      del({"CL100", "community", "65000:100"}), HasSubstr("Successfully"));
  EXPECT_FALSE(lists()[0].communities().has_value());

  auto again = del({"CL100", "community", "65000:100"});
  EXPECT_THAT(
      again,
      HasSubstr(
          "Warning: BGP community-list CL100 has no community 65000:100; "
          "nothing to delete"));
  EXPECT_THAT(again, Not(HasSubstr("Error:")));
  ASSERT_EQ(lists().size(), 1);
  EXPECT_FALSE(lists()[0].communities().has_value());
}

TEST_F(
    CmdDeleteBgpPolicyCommunityListTestFixture,
    deleteCommunityFromValuelessListWarns) {
  configure({"CL100", "description", "no", "values"});

  auto result = del({"CL100", "community", "65000:100"});
  EXPECT_THAT(
      result,
      HasSubstr(
          "Warning: BGP community-list CL100 has no community 65000:100; "
          "nothing to delete"));
  ASSERT_EQ(lists().size(), 1);
  EXPECT_FALSE(lists()[0].communities().has_value());
}

TEST_F(
    CmdDeleteBgpPolicyCommunityListTestFixture,
    deleteCommunityFromUnknownListWarns) {
  auto result = del({"NO-SUCH-LIST", "community", "65000:100"});
  EXPECT_THAT(
      result,
      HasSubstr(
          "Warning: BGP community-list NO-SUCH-LIST does not exist; nothing "
          "to delete"));
  EXPECT_THAT(result, Not(HasSubstr("Error:")));
  EXPECT_FALSE(sessionFileExists())
      << "session file should not exist after a no-op delete";
>>>>>>> 615d477c11c04240d3593f9420b509d3a4661970
}

} // namespace facebook::fboss
