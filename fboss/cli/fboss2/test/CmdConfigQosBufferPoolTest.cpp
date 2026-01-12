/*
 *  Copyright (c) 2004-present, Facebook, Inc.
 *  All rights reserved.
 *
 *  This source code is licensed under the BSD-style license found in the
 *  LICENSE file in the root directory of this source tree. An additional grant
 *  of patent rights can be found in the PATENTS file in the same directory.
 *
 */

#include <boost/filesystem.hpp>
#include <gmock/gmock.h>
#include <gtest/gtest.h>
#include <filesystem>
#include <fstream>

#include "fboss/cli/fboss2/commands/config/qos/buffer_pool/CmdConfigQosBufferPool.h"
#include "fboss/cli/fboss2/commands/config/qos/buffer_pool/CmdConfigQosBufferPoolHeadroomBytes.h"
#include "fboss/cli/fboss2/commands/config/qos/buffer_pool/CmdConfigQosBufferPoolReservedBytes.h"
#include "fboss/cli/fboss2/commands/config/qos/buffer_pool/CmdConfigQosBufferPoolSharedBytes.h"
#include "fboss/cli/fboss2/test/CmdHandlerTestBase.h"
#include "fboss/cli/fboss2/test/TestableConfigSession.h"
#include "fboss/cli/fboss2/utils/PortMap.h"

namespace fs = std::filesystem;

namespace facebook::fboss {

class CmdConfigQosBufferPoolTestFixture : public CmdHandlerTestBase {
 public:
  void SetUp() override {
    CmdHandlerTestBase::SetUp();

    // Create unique test directories
    auto tempBase = fs::temp_directory_path();
    auto uniquePath =
        boost::filesystem::unique_path("fboss_bp_test_%%%%-%%%%-%%%%-%%%%");
    testHomeDir_ = tempBase / (uniquePath.string() + "_home");
    testEtcDir_ = tempBase / (uniquePath.string() + "_etc");

    std::error_code ec;
    if (fs::exists(testHomeDir_)) {
      fs::remove_all(testHomeDir_, ec);
    }
    if (fs::exists(testEtcDir_)) {
      fs::remove_all(testEtcDir_, ec);
    }

    // Create test directories
    fs::create_directories(testHomeDir_);
    fs::create_directories(testEtcDir_ / "coop");
    fs::create_directories(testEtcDir_ / "coop" / "cli");

    // Set environment variables
    setenv("HOME", testHomeDir_.c_str(), 1);
    setenv("USER", "testuser", 1);

    // Create a test system config file
    fs::path initialRevision = testEtcDir_ / "coop" / "cli" / "agent-r1.conf";
    createTestConfig(initialRevision, R"({
  "sw": {
    "ports": [
      {
        "logicalID": 1,
        "name": "eth1/1/1",
        "state": 2,
        "speed": 100000
      }
    ]
  }
})");

    // Create symlink
    systemConfigPath_ = testEtcDir_ / "coop" / "agent.conf";
    fs::create_symlink(initialRevision, systemConfigPath_);

    // Create session config path
    sessionConfigPath_ = testHomeDir_ / ".fboss2" / "agent.conf";
    cliConfigDir_ = testEtcDir_ / "coop" / "cli";
  }

  void TearDown() override {
    // Reset the singleton to ensure tests don't interfere with each other
    TestableConfigSession::setInstance(nullptr);

    std::error_code ec;
    if (fs::exists(testHomeDir_)) {
      fs::remove_all(testHomeDir_, ec);
    }
    if (fs::exists(testEtcDir_)) {
      fs::remove_all(testEtcDir_, ec);
    }
    CmdHandlerTestBase::TearDown();
  }

 protected:
  void createTestConfig(const fs::path& path, const std::string& content) {
    std::ofstream file(path);
    file << content;
    file.close();
  }

  std::string readFile(const fs::path& path) {
    std::ifstream file(path);
    std::stringstream buffer;
    buffer << file.rdbuf();
    return buffer.str();
  }

  fs::path testHomeDir_;
  fs::path testEtcDir_;
  fs::path systemConfigPath_;
  fs::path sessionConfigPath_;
  fs::path cliConfigDir_;
};

// Test BufferPoolName argument validation
TEST_F(CmdConfigQosBufferPoolTestFixture, bufferPoolNameValidation) {
  // Valid names - alphanumeric with underscores and hyphens, starting with
  // letter
  EXPECT_NO_THROW(BufferPoolName({"ingress_pool"}));
  EXPECT_NO_THROW(BufferPoolName({"egress-lossy-pool"}));
  EXPECT_NO_THROW(BufferPoolName({"Pool1"}));
  EXPECT_NO_THROW(BufferPoolName({"a"})); // single character
  EXPECT_NO_THROW(BufferPoolName({"default"}));

  // Empty name should throw
  EXPECT_THROW(BufferPoolName({}), std::invalid_argument);

  // Multiple names should throw
  EXPECT_THROW(BufferPoolName({"pool1", "pool2"}), std::invalid_argument);

  // Invalid names - must start with letter
  EXPECT_THROW(BufferPoolName({"123pool"}), std::invalid_argument);
  EXPECT_THROW(BufferPoolName({"_pool"}), std::invalid_argument);
  EXPECT_THROW(BufferPoolName({"-pool"}), std::invalid_argument);

  // Invalid names - no spaces or special characters
  EXPECT_THROW(BufferPoolName({"pool name"}), std::invalid_argument);
  EXPECT_THROW(BufferPoolName({"pool.name"}), std::invalid_argument);
  EXPECT_THROW(BufferPoolName({"pool@name"}), std::invalid_argument);

  // Invalid names - empty string
  EXPECT_THROW(BufferPoolName({""}), std::invalid_argument);
}

// Test BufferBytesValue argument validation
TEST_F(CmdConfigQosBufferPoolTestFixture, bufferBytesValueValidation) {
  // Valid positive value
  BufferBytesValue validValue({"1000"});
  EXPECT_EQ(validValue.getValue(), 1000);

  // Valid zero value
  BufferBytesValue zeroValue({"0"});
  EXPECT_EQ(zeroValue.getValue(), 0);

  // Empty value should throw
  EXPECT_THROW(BufferBytesValue({}), std::invalid_argument);

  // Negative value should throw
  EXPECT_THROW(BufferBytesValue({"-100"}), std::invalid_argument);

  // Non-numeric value should throw
  EXPECT_THROW(BufferBytesValue({"abc"}), std::invalid_argument);

  // Multiple values should throw
  EXPECT_THROW(BufferBytesValue({"100", "200"}), std::invalid_argument);
}

// Test shared-bytes command creates buffer pool config
TEST_F(CmdConfigQosBufferPoolTestFixture, sharedBytesCreatesBufferPool) {
  TestableConfigSession::setInstance(
      std::make_unique<TestableConfigSession>(
          sessionConfigPath_.string(),
          systemConfigPath_.string(),
          cliConfigDir_.string()));

  auto cmd = CmdConfigQosBufferPoolSharedBytes();
  BufferPoolName poolName({"test_pool"});
  BufferBytesValue sharedBytes({"50000"});

  auto result = cmd.queryClient(localhost(), poolName, sharedBytes);

  EXPECT_THAT(result, ::testing::HasSubstr("Successfully set shared-bytes"));
  EXPECT_THAT(result, ::testing::HasSubstr("test_pool"));
  EXPECT_THAT(result, ::testing::HasSubstr("50000"));

  // Verify the config was actually modified
  auto& config = ConfigSession::getInstance().getAgentConfig();
  auto& switchConfig = *config.sw();
  ASSERT_TRUE(switchConfig.bufferPoolConfigs().has_value());

  auto& bufferPoolConfigs = *switchConfig.bufferPoolConfigs();
  auto it = bufferPoolConfigs.find("test_pool");
  ASSERT_NE(it, bufferPoolConfigs.end());
  EXPECT_EQ(*it->second.sharedBytes(), 50000);
}

// Test headroom-bytes command creates buffer pool config
TEST_F(CmdConfigQosBufferPoolTestFixture, headroomBytesCreatesBufferPool) {
  TestableConfigSession::setInstance(
      std::make_unique<TestableConfigSession>(
          sessionConfigPath_.string(),
          systemConfigPath_.string(),
          cliConfigDir_.string()));

  auto cmd = CmdConfigQosBufferPoolHeadroomBytes();
  BufferPoolName poolName({"headroom_pool"});
  BufferBytesValue headroomBytes({"10000"});

  auto result = cmd.queryClient(localhost(), poolName, headroomBytes);

  EXPECT_THAT(result, ::testing::HasSubstr("Successfully set headroom-bytes"));
  EXPECT_THAT(result, ::testing::HasSubstr("headroom_pool"));
  EXPECT_THAT(result, ::testing::HasSubstr("10000"));

  // Verify the config was actually modified
  auto& config = ConfigSession::getInstance().getAgentConfig();
  auto& switchConfig = *config.sw();
  ASSERT_TRUE(switchConfig.bufferPoolConfigs().has_value());

  auto& bufferPoolConfigs = *switchConfig.bufferPoolConfigs();
  auto it = bufferPoolConfigs.find("headroom_pool");
  ASSERT_NE(it, bufferPoolConfigs.end());
  EXPECT_EQ(*it->second.sharedBytes(), 0); // Default value
  ASSERT_TRUE(it->second.headroomBytes().has_value());
  EXPECT_EQ(*it->second.headroomBytes(), 10000);
}

// Test reserved-bytes command creates buffer pool config
TEST_F(CmdConfigQosBufferPoolTestFixture, reservedBytesCreatesBufferPool) {
  TestableConfigSession::setInstance(
      std::make_unique<TestableConfigSession>(
          sessionConfigPath_.string(),
          systemConfigPath_.string(),
          cliConfigDir_.string()));

  auto cmd = CmdConfigQosBufferPoolReservedBytes();
  BufferPoolName poolName({"reserved_pool"});
  BufferBytesValue reservedBytes({"20000"});

  auto result = cmd.queryClient(localhost(), poolName, reservedBytes);

  EXPECT_THAT(result, ::testing::HasSubstr("Successfully set reserved-bytes"));
  EXPECT_THAT(result, ::testing::HasSubstr("reserved_pool"));
  EXPECT_THAT(result, ::testing::HasSubstr("20000"));

  // Verify the config was actually modified
  auto& config = ConfigSession::getInstance().getAgentConfig();
  auto& switchConfig = *config.sw();
  ASSERT_TRUE(switchConfig.bufferPoolConfigs().has_value());

  auto& bufferPoolConfigs = *switchConfig.bufferPoolConfigs();
  auto it = bufferPoolConfigs.find("reserved_pool");
  ASSERT_NE(it, bufferPoolConfigs.end());
  EXPECT_EQ(*it->second.sharedBytes(), 0); // Default value
  ASSERT_TRUE(it->second.reservedBytes().has_value());
  EXPECT_EQ(*it->second.reservedBytes(), 20000);
}

// Test updating an existing buffer pool
TEST_F(CmdConfigQosBufferPoolTestFixture, updateExistingBufferPool) {
  TestableConfigSession::setInstance(
      std::make_unique<TestableConfigSession>(
          sessionConfigPath_.string(),
          systemConfigPath_.string(),
          cliConfigDir_.string()));

  // First, create a buffer pool with shared-bytes
  auto sharedCmd = CmdConfigQosBufferPoolSharedBytes();
  BufferPoolName poolName({"existing_pool"});
  BufferBytesValue sharedBytes({"30000"});
  sharedCmd.queryClient(localhost(), poolName, sharedBytes);

  // Then, add headroom-bytes to the same pool
  auto headroomCmd = CmdConfigQosBufferPoolHeadroomBytes();
  BufferBytesValue headroomBytes({"5000"});
  headroomCmd.queryClient(localhost(), poolName, headroomBytes);

  // Finally, add reserved-bytes to the same pool
  auto reservedCmd = CmdConfigQosBufferPoolReservedBytes();
  BufferBytesValue reservedBytes({"2000"});
  reservedCmd.queryClient(localhost(), poolName, reservedBytes);

  // Verify all values are set correctly
  auto& config = ConfigSession::getInstance().getAgentConfig();
  auto& switchConfig = *config.sw();
  ASSERT_TRUE(switchConfig.bufferPoolConfigs().has_value());

  auto& bufferPoolConfigs = *switchConfig.bufferPoolConfigs();
  auto it = bufferPoolConfigs.find("existing_pool");
  ASSERT_NE(it, bufferPoolConfigs.end());
  EXPECT_EQ(*it->second.sharedBytes(), 30000);
  ASSERT_TRUE(it->second.headroomBytes().has_value());
  EXPECT_EQ(*it->second.headroomBytes(), 5000);
  ASSERT_TRUE(it->second.reservedBytes().has_value());
  EXPECT_EQ(*it->second.reservedBytes(), 2000);
}

// Test printOutput for shared-bytes command
TEST_F(CmdConfigQosBufferPoolTestFixture, printOutputSharedBytes) {
  auto cmd = CmdConfigQosBufferPoolSharedBytes();
  std::string successMessage =
      "Successfully set shared-bytes for buffer-pool 'my_pool' to 50000";

  std::stringstream buffer;
  std::streambuf* old = std::cout.rdbuf(buffer.rdbuf());
  cmd.printOutput(successMessage);
  std::cout.rdbuf(old);

  EXPECT_EQ(buffer.str(), successMessage + "\n");
}

} // namespace facebook::fboss
