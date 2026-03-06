/*
 *  Copyright (c) 2004-present, Facebook, Inc.
 *  All rights reserved.
 *
 *  This source code is licensed under the BSD-style license found in the
 *  LICENSE file in the root directory of this source tree. An additional grant
 *  of patent rights can be found in the PATENTS file in the same directory.
 *
 */

#include <boost/filesystem/operations.hpp>
#include <folly/json/dynamic.h>
#include <folly/json/json.h>
#include <gmock/gmock.h>
#include <gtest/gtest.h>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <system_error>

#include "fboss/cli/fboss2/gen-cpp2/cli_metadata_types.h"
#include "fboss/cli/fboss2/session/ConfigSession.h"
#include "fboss/cli/fboss2/session/Git.h"
#include "fboss/cli/fboss2/test/CmdHandlerTestBase.h"
#include "fboss/cli/fboss2/test/TestableConfigSession.h"

namespace fs = std::filesystem;

namespace facebook::fboss {

class ConfigSessionTestFixture : public CmdHandlerTestBase {
 public:
  void SetUp() override {
    CmdHandlerTestBase::SetUp();

    // Create unique test directories for each test to avoid conflicts when
    // running tests in parallel
    auto tempBase = fs::temp_directory_path();
    auto uniquePath =
        boost::filesystem::unique_path("fboss_test_%%%%-%%%%-%%%%-%%%%");
    testHomeDir_ = tempBase / (uniquePath.string() + "_home");
    testEtcDir_ = tempBase / (uniquePath.string() + "_etc");

    // Clean up any previous test artifacts (shouldn't exist with unique names)
    std::error_code ec;
    if (fs::exists(testHomeDir_)) {
      fs::remove_all(testHomeDir_, ec);
    }
    if (fs::exists(testEtcDir_)) {
      fs::remove_all(testEtcDir_, ec);
    }

    // Create test directories
    // Structure: systemConfigDir_ = /etc/coop (git repo root)
    //   - agent.conf (symlink -> cli/agent.conf)
    //   - cli/agent.conf (actual config file)
    fs::create_directories(testHomeDir_);
    systemConfigDir_ = testEtcDir_ / "coop";
    fs::create_directories(systemConfigDir_ / "cli");

    // Set environment variables
    setenv("HOME", testHomeDir_.c_str(), 1);
    setenv("USER", "testuser", 1);

    // Create the actual config file at cli/agent.conf
    fs::path cliConfigPath = systemConfigDir_ / "cli" / "agent.conf";
    createTestConfig(cliConfigPath, R"({
  "sw": {
    "ports": [
      {
        "logicalID": 1,
        "name": "eth1/1/1",
        "state": 2,
        "speed": 100000
      },
      {
        "logicalID": 2,
        "name": "eth1/1/2",
        "state": 2,
        "speed": 100000
      }
    ]
  }
})");

    // Create symlink at /etc/coop/agent.conf -> cli/agent.conf
    fs::create_symlink("cli/agent.conf", systemConfigDir_ / "agent.conf");

    // Initialize Git repository and create initial commit
    Git git(systemConfigDir_.string());
    git.init();
    git.commit({cliConfigPath.string()}, "Initial commit");
  }

  void TearDown() override {
    // Clean up test directories
    // Use error_code to avoid throwing exceptions in TearDown
    std::error_code ec;
    if (fs::exists(testHomeDir_)) {
      fs::remove_all(testHomeDir_, ec);
      if (ec) {
        std::cerr << "Warning: Failed to remove " << testHomeDir_ << ": "
                  << ec.message() << std::endl;
      }
    }
    if (fs::exists(testEtcDir_)) {
      fs::remove_all(testEtcDir_, ec);
      if (ec) {
        std::cerr << "Warning: Failed to remove " << testEtcDir_ << ": "
                  << ec.message() << std::endl;
      }
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
  fs::path systemConfigDir_; // /etc/coop (git repo root)
};

TEST_F(ConfigSessionTestFixture, sessionInitialization) {
  // Initially, session directory should not exist
  fs::path sessionDir = testHomeDir_ / ".fboss2";
  fs::path sessionConfig = sessionDir / "agent.conf";
<<<<<<< HEAD
  fs::path cliConfigPath = getTestEtcDir() / "coop" / "cli" / "agent.conf";
||||||| 8908ebf139
=======
  fs::path cliConfigPath = systemConfigDir_ / "cli" / "agent.conf";
>>>>>>> c17655f13960093f57bb9baa2709891f330dd442
  EXPECT_FALSE(fs::exists(sessionDir));

  // Creating a ConfigSession should create the directory and copy the config
<<<<<<< HEAD
  TestableConfigSession session(
      sessionDir.string(), (getTestEtcDir() / "coop").string());
||||||| 8908ebf139
  // getSystemConfigPath() is already a symlink created in SetUp()
  TestableConfigSession session(
      sessionConfig.string(),
      getSystemConfigPath().string(),
      (getTestEtcDir() / "coop" / "cli").string());
=======
  TestableConfigSession session(sessionDir.string(), systemConfigDir_.string());
>>>>>>> c17655f13960093f57bb9baa2709891f330dd442

  // Verify the directory was created
  EXPECT_TRUE(fs::exists(sessionDir));
  EXPECT_TRUE(session.sessionExists());
  EXPECT_TRUE(fs::exists(sessionConfig));

  // Verify content was copied correctly (reads via symlink)
  std::string systemContent = readFile(cliConfigPath);
  std::string sessionContent = readFile(sessionConfig);
  EXPECT_EQ(systemContent, sessionContent);
}

TEST_F(ConfigSessionTestFixture, sessionConfigModified) {
  fs::path sessionDir = testHomeDir_ / ".fboss2";
  fs::path sessionConfig = sessionDir / "agent.conf";
<<<<<<< HEAD
  fs::path cliConfigPath = getTestEtcDir() / "coop" / "cli" / "agent.conf";
||||||| 8908ebf139
=======
  fs::path cliConfigPath = systemConfigDir_ / "cli" / "agent.conf";
>>>>>>> c17655f13960093f57bb9baa2709891f330dd442

  // Create a ConfigSession
<<<<<<< HEAD
  TestableConfigSession session(
      sessionDir.string(), (getTestEtcDir() / "coop").string());
||||||| 8908ebf139
  // getSystemConfigPath() is already a symlink created in SetUp()
  TestableConfigSession session(
      sessionConfig.string(),
      getSystemConfigPath().string(),
      (getTestEtcDir() / "coop" / "cli").string());
=======
  TestableConfigSession session(sessionDir.string(), systemConfigDir_.string());
>>>>>>> c17655f13960093f57bb9baa2709891f330dd442

  // Modify the session config through the ConfigSession API
  auto& config = session.getAgentConfig();
  auto& ports = *config.sw()->ports();
  ASSERT_FALSE(ports.empty());
  ports[0].description() = "Modified port";
  session.setCommandLine("config interface eth1/1/1 description Modified port");
  session.saveConfig(cli::ServiceType::AGENT, cli::ConfigActionLevel::HITLESS);

  // Verify session config is modified
  std::string sessionContent = readFile(sessionConfig);
  std::string systemContent = readFile(cliConfigPath);
  EXPECT_NE(sessionContent, systemContent);
  EXPECT_THAT(sessionContent, ::testing::HasSubstr("Modified port"));
}

TEST_F(ConfigSessionTestFixture, sessionCommit) {
  fs::path sessionDir = testHomeDir_ / ".fboss2";
  fs::path sessionConfig = sessionDir / "agent.conf";
<<<<<<< HEAD
  fs::path cliConfigPath = getTestEtcDir() / "coop" / "cli" / "agent.conf";
||||||| 8908ebf139
  fs::path cliConfigDir = getTestEtcDir() / "coop" / "cli";

  // Verify old symlink exists (created in SetUp)
  EXPECT_TRUE(fs::is_symlink(getSystemConfigPath()));
  EXPECT_EQ(
      fs::read_symlink(getSystemConfigPath()), cliConfigDir / "agent-r1.conf");
=======
  fs::path cliConfigPath = systemConfigDir_ / "cli" / "agent.conf";
>>>>>>> c17655f13960093f57bb9baa2709891f330dd442

  // Setup mock agent server
  setupMockedAgentServer();
  EXPECT_CALL(getMockAgent(), reloadConfig()).Times(2);

  std::string firstCommitSha;
  std::string secondCommitSha;

  // First commit: Create a ConfigSession and commit a change
  {
    TestableConfigSession session(
<<<<<<< HEAD
        sessionDir.string(), (getTestEtcDir() / "coop").string());

    // Simulate a CLI command being tracked
    session.addCommand("config interface eth1/1/1 description First commit");
||||||| 8908ebf139
        sessionConfig.string(),
        getSystemConfigPath().string(),
        cliConfigDir.string());
=======
        sessionDir.string(), systemConfigDir_.string());

    // Simulate a CLI command being tracked
    session.setCommandLine(
        "config interface eth1/1/1 description First commit");
>>>>>>> c17655f13960093f57bb9baa2709891f330dd442

    // Modify the session config
    auto& config = session.getAgentConfig();
    auto& ports = *config.sw()->ports();
    ASSERT_FALSE(ports.empty());
    ports[0].description() = "First commit";
    session.saveConfig(
        cli::ServiceType::AGENT, cli::ConfigActionLevel::HITLESS);

    // Commit the session
    auto result = session.commit(localhost());

    // Verify session config no longer exists (removed after commit)
    EXPECT_FALSE(fs::exists(sessionConfig));

    // Verify commit SHA was returned
    EXPECT_FALSE(result.commitSha.empty());
    EXPECT_EQ(result.commitSha.length(), 40); // Full SHA1 is 40 chars
    firstCommitSha = result.commitSha;

    // Verify metadata file was created alongside the config revision
<<<<<<< HEAD
    fs::path targetMetadata =
        getTestEtcDir() / "coop" / "cli" / "cli_metadata.json";
||||||| 8908ebf139
    fs::path targetMetadata = cliConfigDir / "agent-r2.metadata.json";
=======
    fs::path targetMetadata = systemConfigDir_ / "cli" / "cli_metadata.json";
>>>>>>> c17655f13960093f57bb9baa2709891f330dd442
    EXPECT_TRUE(fs::exists(targetMetadata));

    // Verify system config was updated
    EXPECT_THAT(readFile(cliConfigPath), ::testing::HasSubstr("First commit"));
  }

  // Second commit: Create a new session and verify it's based on first commit
  {
    TestableConfigSession session(
<<<<<<< HEAD
        sessionDir.string(), (getTestEtcDir() / "coop").string());
||||||| 8908ebf139
        sessionConfig.string(),
        getSystemConfigPath().string(),
        cliConfigDir.string());
=======
        sessionDir.string(), systemConfigDir_.string());
>>>>>>> c17655f13960093f57bb9baa2709891f330dd442

    // Simulate a CLI command being tracked
<<<<<<< HEAD
    session.addCommand("config interface eth1/1/1 description Second commit");
||||||| 8908ebf139
    // Verify the new session is based on r2 (the latest committed revision)
=======
    session.setCommandLine(
        "config interface eth1/1/1 description Second commit");
>>>>>>> c17655f13960093f57bb9baa2709891f330dd442

    // Verify the new session is based on the latest committed revision
    auto& config = session.getAgentConfig();
    auto& ports = *config.sw()->ports();
    ASSERT_FALSE(ports.empty());
    EXPECT_EQ(*ports[0].description(), "First commit");

    // Make another change to the same port
    ports[0].description() = "Second commit";
    session.saveConfig(
        cli::ServiceType::AGENT, cli::ConfigActionLevel::HITLESS);

    // Commit the second change
    auto result = session.commit(localhost());

    // Verify new commit SHA was returned
    EXPECT_FALSE(result.commitSha.empty());
    EXPECT_NE(result.commitSha, firstCommitSha);
    secondCommitSha = result.commitSha;

    // Verify metadata file was created alongside the config revision
<<<<<<< HEAD
    fs::path targetMetadata =
        getTestEtcDir() / "coop" / "cli" / "cli_metadata.json";
||||||| 8908ebf139
    fs::path targetMetadata = cliConfigDir / "agent-r3.metadata.json";
=======
    fs::path targetMetadata = systemConfigDir_ / "cli" / "cli_metadata.json";
>>>>>>> c17655f13960093f57bb9baa2709891f330dd442
    EXPECT_TRUE(fs::exists(targetMetadata));

    // Verify system config was updated
    EXPECT_THAT(readFile(cliConfigPath), ::testing::HasSubstr("Second commit"));

    // Verify Git history has all commits
    auto& git = session.getGit();
    auto commits = git.log(cliConfigPath.string());
    EXPECT_EQ(commits.size(), 3); // Initial + 2 commits

    // Verify metadata file was also committed to git
    auto metadataCommits = git.log(targetMetadata.string());
    EXPECT_EQ(metadataCommits.size(), 2); // 2 commits
  }
}

// Ensure commit() works on a newly initialized session
// This verifies that initializeSession() creates the metadata file
TEST_F(ConfigSessionTestFixture, commitOnNewlyInitializedSession) {
<<<<<<< HEAD
  fs::path sessionDir = getTestHomeDir() / ".fboss2";
  fs::path cliConfigDir = getTestEtcDir() / "coop" / "cli";
||||||| 8908ebf139
  fs::path sessionDir = getTestHomeDir() / ".fboss2";
  fs::path sessionConfig = sessionDir / "agent.conf";
  fs::path cliConfigDir = getTestEtcDir() / "coop" / "cli";
=======
  fs::path sessionDir = testHomeDir_ / ".fboss2";
  fs::path cliConfigDir = systemConfigDir_ / "cli";
>>>>>>> c17655f13960093f57bb9baa2709891f330dd442

  // Setup mock agent server
  setupMockedAgentServer();
  EXPECT_CALL(getMockAgent(), reloadConfig()).Times(1);

  // Create a new session
  // This tests that metadata file is created during session initialization
<<<<<<< HEAD
  TestableConfigSession session(
      sessionDir.string(), (getTestEtcDir() / "coop").string());
||||||| 8908ebf139
  TestableConfigSession session(
      sessionConfig.string(),
      getSystemConfigPath().string(),
      cliConfigDir.string());
=======
  TestableConfigSession session(sessionDir.string(), systemConfigDir_.string());
>>>>>>> c17655f13960093f57bb9baa2709891f330dd442

  // Verify metadata file was created during session initialization
  fs::path metadataPath = sessionDir / "cli_metadata.json";
  EXPECT_TRUE(fs::exists(metadataPath));

  // Make a change so commit has something to commit
  auto& config = session.getAgentConfig();
  auto& ports = *config.sw()->ports();
  ASSERT_FALSE(ports.empty());
  ports[0].description() = "Test change for commit";
<<<<<<< HEAD
||||||| 8908ebf139
  // Make no changes to the session. It's initialized but that's it.
=======
  session.setCommandLine(
      "config interface eth1/1/1 description Test change for commit");
>>>>>>> c17655f13960093f57bb9baa2709891f330dd442
  session.saveConfig(cli::ServiceType::AGENT, cli::ConfigActionLevel::HITLESS);

  // Commit should succeed
  auto result = session.commit(localhost());
  EXPECT_FALSE(result.commitSha.empty());

  // Verify metadata file was copied to CLI config directory
  fs::path targetMetadata = cliConfigDir / "cli_metadata.json";
  EXPECT_TRUE(fs::exists(targetMetadata));
}

TEST_F(ConfigSessionTestFixture, multipleChangesInOneSession) {
  fs::path sessionDir = testHomeDir_ / ".fboss2";
  fs::path sessionConfig = sessionDir / "agent.conf";

  // Create a ConfigSession
<<<<<<< HEAD
  TestableConfigSession session(
      sessionDir.string(), (getTestEtcDir() / "coop").string());
||||||| 8908ebf139
  // getSystemConfigPath() is already a symlink created in SetUp()
  TestableConfigSession session(
      sessionConfig.string(),
      getSystemConfigPath().string(),
      (getTestEtcDir() / "coop" / "cli").string());
=======
  TestableConfigSession session(sessionDir.string(), systemConfigDir_.string());
>>>>>>> c17655f13960093f57bb9baa2709891f330dd442

  // Make first change
  auto& config = session.getAgentConfig();
  auto& ports = *config.sw()->ports();
  ASSERT_FALSE(ports.empty());
  ports[0].description() = "Change 1";
  session.setCommandLine("config interface eth1/1/1 description Change 1");
  session.saveConfig(cli::ServiceType::AGENT, cli::ConfigActionLevel::HITLESS);
  EXPECT_THAT(readFile(sessionConfig), ::testing::HasSubstr("Change 1"));

  // Make second change
  ports[0].description() = "Change 2";
  session.setCommandLine("config interface eth1/1/1 description Change 2");
  session.saveConfig(cli::ServiceType::AGENT, cli::ConfigActionLevel::HITLESS);
  EXPECT_THAT(readFile(sessionConfig), ::testing::HasSubstr("Change 2"));

  // Make third change
  ports[0].description() = "Change 3";
  session.setCommandLine("config interface eth1/1/1 description Change 3");
  session.saveConfig(cli::ServiceType::AGENT, cli::ConfigActionLevel::HITLESS);
  EXPECT_THAT(readFile(sessionConfig), ::testing::HasSubstr("Change 3"));
}

TEST_F(ConfigSessionTestFixture, sessionPersistsAcrossCommands) {
  fs::path sessionDir = testHomeDir_ / ".fboss2";
  fs::path sessionConfig = sessionDir / "agent.conf";

  // Create first ConfigSession and modify config
  {
    TestableConfigSession session1(
<<<<<<< HEAD
        sessionDir.string(), (getTestEtcDir() / "coop").string());
||||||| 8908ebf139
        sessionConfig.string(),
        getSystemConfigPath().string(),
        (getTestEtcDir() / "coop" / "cli").string());
=======
        sessionDir.string(), systemConfigDir_.string());
>>>>>>> c17655f13960093f57bb9baa2709891f330dd442

    auto& config = session1.getAgentConfig();
    auto& ports = *config.sw()->ports();
    ASSERT_FALSE(ports.empty());
    ports[0].description() = "Persistent change";
    session1.setCommandLine(
        "config interface eth1/1/1 description Persistent change");
    session1.saveConfig(
        cli::ServiceType::AGENT, cli::ConfigActionLevel::HITLESS);
  }

  // Verify session persists (file still exists with same content)
  EXPECT_TRUE(fs::exists(sessionConfig));
  EXPECT_THAT(
      readFile(sessionConfig), ::testing::HasSubstr("Persistent change"));

  // Create another ConfigSession to simulate another command reading the
  // session
  {
    TestableConfigSession session2(
<<<<<<< HEAD
        sessionDir.string(), (getTestEtcDir() / "coop").string());
||||||| 8908ebf139
        sessionConfig.string(),
        getSystemConfigPath().string(),
        (getTestEtcDir() / "coop" / "cli").string());
=======
        sessionDir.string(), systemConfigDir_.string());
>>>>>>> c17655f13960093f57bb9baa2709891f330dd442

    auto& config = session2.getAgentConfig();
    auto& ports = *config.sw()->ports();
    ASSERT_FALSE(ports.empty());
    // Verify the change persisted
    EXPECT_EQ(*ports[0].description(), "Persistent change");
  }
}

TEST_F(ConfigSessionTestFixture, configRollbackOnFailure) {
<<<<<<< HEAD
  fs::path sessionDir = getTestHomeDir() / ".fboss2";
||||||| 8908ebf139
TEST_F(ConfigSessionTestFixture, symlinkRollbackOnFailure) {
  fs::path sessionDir = getTestHomeDir() / ".fboss2";
=======
  fs::path sessionDir = testHomeDir_ / ".fboss2";
>>>>>>> c17655f13960093f57bb9baa2709891f330dd442
  fs::path sessionConfig = sessionDir / "agent.conf";
<<<<<<< HEAD
  fs::path cliConfigPath = getTestEtcDir() / "coop" / "cli" / "agent.conf";
||||||| 8908ebf139
  fs::path cliConfigDir = getTestEtcDir() / "coop" / "cli";
=======
  fs::path cliConfigPath = systemConfigDir_ / "cli" / "agent.conf";
>>>>>>> c17655f13960093f57bb9baa2709891f330dd442

  // Save the original config content
  std::string originalContent = readFile(cliConfigPath);

  // Setup mock agent server to fail reloadConfig
  setupMockedAgentServer();
  EXPECT_CALL(getMockAgent(), reloadConfig())
      .WillOnce(::testing::Throw(std::runtime_error("Reload failed")))
      .WillOnce(::testing::Return());

  // Create a ConfigSession and try to commit
<<<<<<< HEAD
  TestableConfigSession session(
      sessionDir.string(), (getTestEtcDir() / "coop").string());
||||||| 8908ebf139
  // getSystemConfigPath() is already a symlink to agent-r1.conf created in
  // SetUp()
  TestableConfigSession session(
      sessionConfig.string(),
      getSystemConfigPath().string(),
      cliConfigDir.string());
=======
  TestableConfigSession session(sessionDir.string(), systemConfigDir_.string());
>>>>>>> c17655f13960093f57bb9baa2709891f330dd442

  auto& config = session.getAgentConfig();
  auto& ports = *config.sw()->ports();
  ASSERT_FALSE(ports.empty());
  ports[0].description() = "Failed change";
  session.setCommandLine("config interface eth1/1/1 description Failed change");
  session.saveConfig(cli::ServiceType::AGENT, cli::ConfigActionLevel::HITLESS);

  // Commit should fail and rollback the config
  EXPECT_THROW(session.commit(localhost()), std::runtime_error);

  // Verify config was rolled back to original content
  std::string currentContent = readFile(cliConfigPath);
  EXPECT_EQ(currentContent, originalContent);

  // Verify session config still exists (not removed on failed commit)
  EXPECT_TRUE(fs::exists(sessionConfig));
}

TEST_F(ConfigSessionTestFixture, concurrentCommits) {
<<<<<<< HEAD
  fs::path cliConfigPath = getTestEtcDir() / "coop" / "cli" / "agent.conf";
||||||| 8908ebf139
TEST_F(ConfigSessionTestFixture, atomicRevisionCreation) {
  fs::path cliConfigDir = getTestEtcDir() / "coop" / "cli";
=======
  fs::path cliConfigPath = systemConfigDir_ / "cli" / "agent.conf";
>>>>>>> c17655f13960093f57bb9baa2709891f330dd442

  // Setup mock agent server
  setupMockedAgentServer();
  EXPECT_CALL(getMockAgent(), reloadConfig()).Times(2);

  // Run two sequential commits to test Git commit functionality
  // Note: Git doesn't handle truly concurrent commits well due to index.lock,
  // so we run them sequentially to avoid race conditions.
  std::string commitSha1;
  std::string commitSha2;

  // First commit
  {
<<<<<<< HEAD
    fs::path sessionDir = getTestHomeDir() / ".fboss2_user1";
||||||| 8908ebf139
  auto commitTask = [&](const std::string& sessionName,
                        const std::string& description,
                        std::atomic<int>& rev) {
    fs::path sessionDir = getTestHomeDir() / sessionName;
    fs::path sessionConfig = sessionDir / "agent.conf";
=======
    fs::path sessionDir = testHomeDir_ / ".fboss2_user1";
>>>>>>> c17655f13960093f57bb9baa2709891f330dd442

    TestableConfigSession session(
<<<<<<< HEAD
        sessionDir.string(), (getTestEtcDir() / "coop").string());
||||||| 8908ebf139
        sessionConfig.string(),
        getSystemConfigPath().string(),
        cliConfigDir.string());
=======
        sessionDir.string(), systemConfigDir_.string());
>>>>>>> c17655f13960093f57bb9baa2709891f330dd442

    auto& config = session.getAgentConfig();
    auto& ports = *config.sw()->ports();
    ASSERT_FALSE(ports.empty());
    ports[0].description() = "First commit";
<<<<<<< HEAD
||||||| 8908ebf139
    ports[0].description() = description;
    session.setCommandLine(
        "config interface eth1/1/1 description " + description);
=======
    session.setCommandLine(
        "config interface eth1/1/1 description First commit");
>>>>>>> c17655f13960093f57bb9baa2709891f330dd442
    session.saveConfig(
        cli::ServiceType::AGENT, cli::ConfigActionLevel::HITLESS);

    auto result = session.commit(localhost());
    commitSha1 = result.commitSha;
  }

  // Second commit
  {
<<<<<<< HEAD
    fs::path sessionDir = getTestHomeDir() / ".fboss2_user2";
||||||| 8908ebf139
  std::thread thread1(
      commitTask, ".fboss2_user1", "First commit", std::ref(revision1));
  std::thread thread2(
      commitTask, ".fboss2_user2", "Second commit", std::ref(revision2));

  thread1.join();
  thread2.join();

  // Both commits should succeed with different revision numbers
  EXPECT_NE(revision1.load(), 0);
  EXPECT_NE(revision2.load(), 0);
  EXPECT_NE(revision1.load(), revision2.load());

  // Both should be either r2 or r3 (one gets r2, the other gets r3)
  EXPECT_TRUE(
      (revision1.load() == 2 && revision2.load() == 3) ||
      (revision1.load() == 3 && revision2.load() == 2));

  // Both revision files should exist
  EXPECT_TRUE(fs::exists(cliConfigDir / "agent-r2.conf"));
  EXPECT_TRUE(fs::exists(cliConfigDir / "agent-r3.conf"));

  // Verify the content of each revision matches what was committed
  std::string r2Content = readFile(cliConfigDir / "agent-r2.conf");
  std::string r3Content = readFile(cliConfigDir / "agent-r3.conf");
  EXPECT_TRUE(
      (r2Content.find("First commit") != std::string::npos &&
       r3Content.find("Second commit") != std::string::npos) ||
      (r2Content.find("Second commit") != std::string::npos &&
       r3Content.find("First commit") != std::string::npos));
}

TEST_F(ConfigSessionTestFixture, concurrentSessionCreationSameUser) {
  fs::path cliConfigDir = getTestEtcDir() / "coop" / "cli";

  // Setup mock agent server
  // Either 1 or 2 commits might succeed depending on the race
  setupMockedAgentServer();
  EXPECT_CALL(getMockAgent(), reloadConfig()).Times(testing::Between(1, 2));

  // Test concurrent session creation and commits for the SAME user
  // This tests the race conditions in:
  // 1. ensureDirectoryExists() - concurrent directory creation
  // 2. copySystemConfigToSession() - concurrent session file creation
  // 3. saveConfig() - concurrent writes to the same session file
  // 4. atomicSymlinkUpdate() - concurrent symlink updates
  //
  // Note: When two threads share the same session file, they race to modify it.
  // The atomic operations ensure no crashes or corruption. However, if one
  // thread commits and deletes the session files before the other thread
  // calls commit(), the second thread will get "No config session exists".
  // This is a valid race outcome - the important thing is no crashes.
  std::atomic<int> revision1{0};
  std::atomic<int> revision2{0};
  std::atomic<bool> thread1NoSession{false};
  std::atomic<bool> thread2NoSession{false};

  auto commitTask = [&](const std::string& description,
                        std::atomic<int>& rev,
                        std::atomic<bool>& noSession) {
    // Both threads use the SAME session path
    fs::path sessionDir = getTestHomeDir() / ".fboss2_shared";
    fs::path sessionConfig = sessionDir / "agent.conf";
=======
    fs::path sessionDir = testHomeDir_ / ".fboss2_user2";
>>>>>>> c17655f13960093f57bb9baa2709891f330dd442

    TestableConfigSession session(
<<<<<<< HEAD
        sessionDir.string(), (getTestEtcDir() / "coop").string());
||||||| 8908ebf139
        sessionConfig.string(),
        getSystemConfigPath().string(),
        cliConfigDir.string());
=======
        sessionDir.string(), systemConfigDir_.string());
>>>>>>> c17655f13960093f57bb9baa2709891f330dd442

    auto& config = session.getAgentConfig();
    auto& ports = *config.sw()->ports();
    ASSERT_FALSE(ports.empty());
    ports[0].description() = "Second commit";
<<<<<<< HEAD
||||||| 8908ebf139
    ports[0].description() = description;
    session.setCommandLine(
        "config interface eth1/1/1 description " + description);
=======
    session.setCommandLine(
        "config interface eth1/1/1 description Second commit");
>>>>>>> c17655f13960093f57bb9baa2709891f330dd442
    session.saveConfig(
        cli::ServiceType::AGENT, cli::ConfigActionLevel::HITLESS);

    auto result = session.commit(localhost());
    commitSha2 = result.commitSha;
  }

  // Both commits should succeed with different commit SHAs
  EXPECT_FALSE(commitSha1.empty());
  EXPECT_FALSE(commitSha2.empty());
  EXPECT_NE(commitSha1, commitSha2);

  // Verify Git history contains both commits
<<<<<<< HEAD
  Git git((getTestEtcDir() / "coop").string());
||||||| 8908ebf139
  // The history command would list all three revisions with their metadata
=======
  Git git(systemConfigDir_.string());
>>>>>>> c17655f13960093f57bb9baa2709891f330dd442
  auto commits = git.log(cliConfigPath.string());
  EXPECT_GE(commits.size(), 3); // Initial + 2 commits
}

TEST_F(ConfigSessionTestFixture, rollbackToSpecificCommit) {
  // This test calls the rollback() method with a specific commit SHA
<<<<<<< HEAD
  fs::path sessionDir = getTestHomeDir() / ".fboss2";
  fs::path cliConfigPath = getTestEtcDir() / "coop" / "cli" / "agent.conf";
  fs::path metadataPath =
      getTestEtcDir() / "coop" / "cli" / "cli_metadata.json";
||||||| 8908ebf139
TEST_F(ConfigSessionTestFixture, revisionNumberExtraction) {
  // Test the revision number extraction logic
  fs::path cliConfigDir = getTestEtcDir() / "coop" / "cli";

  // Create files with various revision numbers
  createTestConfig(cliConfigDir / "agent-r1.conf", R"({})");
  createTestConfig(cliConfigDir / "agent-r42.conf", R"({})");
  createTestConfig(cliConfigDir / "agent-r999.conf", R"({})");

  // Verify files exist
  EXPECT_TRUE(fs::exists(cliConfigDir / "agent-r1.conf"));
  EXPECT_TRUE(fs::exists(cliConfigDir / "agent-r42.conf"));
  EXPECT_TRUE(fs::exists(cliConfigDir / "agent-r999.conf"));

  // Test extractRevisionNumber() method
  EXPECT_EQ(
      ConfigSession::extractRevisionNumber(
          (cliConfigDir / "agent-r1.conf").string()),
      1);
  EXPECT_EQ(
      ConfigSession::extractRevisionNumber(
          (cliConfigDir / "agent-r42.conf").string()),
      42);
  EXPECT_EQ(
      ConfigSession::extractRevisionNumber(
          (cliConfigDir / "agent-r999.conf").string()),
      999);
}

TEST_F(ConfigSessionTestFixture, rollbackCreatesNewRevision) {
  // This test actually calls the rollback() method with a specific revision
  fs::path cliConfigDir = getTestEtcDir() / "coop" / "cli";
  fs::path symlinkPath = getTestEtcDir() / "coop" / "agent.conf";
  fs::path sessionConfigPath = getTestHomeDir() / ".fboss2" / "agent.conf";

  // Remove the regular file created by SetUp
  if (fs::exists(symlinkPath)) {
    fs::remove(symlinkPath);
  }

  // Create revision files (simulating previous commits)
  createTestConfig(cliConfigDir / "agent-r1.conf", R"({"revision": 1})");
  createTestConfig(cliConfigDir / "agent-r2.conf", R"({"revision": 2})");
  createTestConfig(cliConfigDir / "agent-r3.conf", R"({"revision": 3})");

  // Create symlink pointing to r3 (current revision)
  fs::create_symlink(cliConfigDir / "agent-r3.conf", symlinkPath);

  // Verify initial state
  EXPECT_TRUE(fs::is_symlink(symlinkPath));
  EXPECT_EQ(fs::read_symlink(symlinkPath), cliConfigDir / "agent-r3.conf");
=======
  fs::path sessionDir = testHomeDir_ / ".fboss2";
  fs::path cliConfigPath = systemConfigDir_ / "cli" / "agent.conf";
  fs::path metadataPath = systemConfigDir_ / "cli" / "cli_metadata.json";
>>>>>>> c17655f13960093f57bb9baa2709891f330dd442

  // Setup mock agent server
  setupMockedAgentServer();
  // 2 commits + 1 rollback = 3 reloadConfig calls
  EXPECT_CALL(getMockAgent(), reloadConfig()).Times(3);

  // Create a session and make several commits to build history
  std::string firstCommitSha;
  std::string secondCommitSha;
  {
    TestableConfigSession session(
<<<<<<< HEAD
        sessionDir.string(), (getTestEtcDir() / "coop").string());
||||||| 8908ebf139
  // Expect reloadConfig to be called once
  EXPECT_CALL(getMockAgent(), reloadConfig()).Times(1);
=======
        sessionDir.string(), systemConfigDir_.string());
>>>>>>> c17655f13960093f57bb9baa2709891f330dd442

    // Simulate CLI command for first commit
<<<<<<< HEAD
    session.addCommand("config interface eth1/1/1 description First version");
||||||| 8908ebf139
  // Create a testable ConfigSession with test paths
  TestableConfigSession session(
      sessionConfigPath.string(), symlinkPath.string(), cliConfigDir.string());
=======
    session.setCommandLine(
        "config interface eth1/1/1 description First version");
>>>>>>> c17655f13960093f57bb9baa2709891f330dd442

    // First commit
    auto& config1 = session.getAgentConfig();
    (*config1.sw()->ports())[0].description() = "First version";
    session.saveConfig(
        cli::ServiceType::AGENT, cli::ConfigActionLevel::HITLESS);
    auto result1 = session.commit(localhost());
    firstCommitSha = result1.commitSha;

    // Second commit (need new session after commit)
  }
  {
    TestableConfigSession session(
<<<<<<< HEAD
        sessionDir.string(), (getTestEtcDir() / "coop").string());
||||||| 8908ebf139
  // Verify rollback created a new revision (r4)
  EXPECT_EQ(newRevision, 4);
  EXPECT_TRUE(fs::is_symlink(symlinkPath));
  EXPECT_EQ(fs::read_symlink(symlinkPath), cliConfigDir / "agent-r4.conf");
  EXPECT_TRUE(fs::exists(cliConfigDir / "agent-r4.conf"));
=======
        sessionDir.string(), systemConfigDir_.string());
>>>>>>> c17655f13960093f57bb9baa2709891f330dd442

    // Simulate CLI command for second commit
<<<<<<< HEAD
    session.addCommand("config interface eth1/1/1 description Second version");
||||||| 8908ebf139
  // Verify r4 has same content as r1 (the target revision)
  EXPECT_EQ(
      readFile(cliConfigDir / "agent-r1.conf"),
      readFile(cliConfigDir / "agent-r4.conf"));
=======
    session.setCommandLine(
        "config interface eth1/1/1 description Second version");
>>>>>>> c17655f13960093f57bb9baa2709891f330dd442

    auto& config2 = session.getAgentConfig();
    (*config2.sw()->ports())[0].description() = "Second version";
    session.saveConfig(
        cli::ServiceType::AGENT, cli::ConfigActionLevel::HITLESS);
    auto result2 = session.commit(localhost());
    secondCommitSha = result2.commitSha;
  }

  // Verify current content is "Second version"
  EXPECT_THAT(readFile(cliConfigPath), ::testing::HasSubstr("Second version"));
  // Verify current metadata contains second command
  EXPECT_THAT(
      readFile(metadataPath), ::testing::HasSubstr("description Second"));

  // Now rollback to first commit
  {
    TestableConfigSession session(
<<<<<<< HEAD
        sessionDir.string(), (getTestEtcDir() / "coop").string());
||||||| 8908ebf139
  // Create symlink pointing to r3 (current revision)
  fs::create_symlink(cliConfigDir / "agent-r3.conf", symlinkPath);
=======
        sessionDir.string(), systemConfigDir_.string());
>>>>>>> c17655f13960093f57bb9baa2709891f330dd442

    std::string rollbackSha = session.rollback(localhost(), firstCommitSha);

    // Verify rollback created a new commit
    EXPECT_FALSE(rollbackSha.empty());
    EXPECT_NE(rollbackSha, firstCommitSha);
    EXPECT_NE(rollbackSha, secondCommitSha);

    // Verify config content is now "First version"
    EXPECT_THAT(readFile(cliConfigPath), ::testing::HasSubstr("First version"));

    // Verify metadata was also rolled back to first version
    std::string metadataContent = readFile(metadataPath);
    EXPECT_THAT(metadataContent, ::testing::HasSubstr("description First"));
    EXPECT_THAT(
        metadataContent,
        ::testing::Not(::testing::HasSubstr("description Second")));

    // Verify Git history has the rollback commit
    auto& git = session.getGit();
    auto commits = git.log(cliConfigPath.string());
    EXPECT_EQ(commits.size(), 4); // Initial + 2 commits + rollback

    // Verify metadata file history
    auto metadataCommits = git.log(metadataPath.string());
    EXPECT_EQ(metadataCommits.size(), 3); // 2 commits + rollback
  }
}

TEST_F(ConfigSessionTestFixture, rollbackToPreviousCommit) {
  // This test calls the rollback() method without a commit SHA argument
  // to rollback to the previous commit
<<<<<<< HEAD
  fs::path sessionDir = getTestHomeDir() / ".fboss2";
  fs::path cliConfigPath = getTestEtcDir() / "coop" / "cli" / "agent.conf";
||||||| 8908ebf139
  // Verify initial state
  EXPECT_TRUE(fs::is_symlink(symlinkPath));
  EXPECT_EQ(fs::read_symlink(symlinkPath), cliConfigDir / "agent-r3.conf");
=======
  fs::path sessionDir = testHomeDir_ / ".fboss2";
  fs::path cliConfigPath = systemConfigDir_ / "cli" / "agent.conf";
>>>>>>> c17655f13960093f57bb9baa2709891f330dd442

  // Setup mock agent server
  setupMockedAgentServer();
  // 2 commits + 1 rollback = 3 reloadConfig calls
  EXPECT_CALL(getMockAgent(), reloadConfig()).Times(3);

  // Create commits to build history
  {
    TestableConfigSession session(
<<<<<<< HEAD
        sessionDir.string(), (getTestEtcDir() / "coop").string());
||||||| 8908ebf139
  // Expect reloadConfig to be called once
  EXPECT_CALL(getMockAgent(), reloadConfig()).Times(1);
=======
        sessionDir.string(), systemConfigDir_.string());
>>>>>>> c17655f13960093f57bb9baa2709891f330dd442

    auto& config1 = session.getAgentConfig();
    (*config1.sw()->ports())[0].description() = "First version";
<<<<<<< HEAD
    session.saveConfig(
        cli::ServiceType::AGENT, cli::ConfigActionLevel::HITLESS);
    session.commit(localhost());
  }
  {
    TestableConfigSession session(
        sessionDir.string(), (getTestEtcDir() / "coop").string());
||||||| 8908ebf139
  // Create a testable ConfigSession with test paths
  TestableConfigSession session(
      sessionConfigPath.string(), symlinkPath.string(), cliConfigDir.string());
=======
    session.setCommandLine(
        "config interface eth1/1/1 description First version");
    session.saveConfig(
        cli::ServiceType::AGENT, cli::ConfigActionLevel::HITLESS);
    session.commit(localhost());
  }
  {
    TestableConfigSession session(
        sessionDir.string(), systemConfigDir_.string());
>>>>>>> c17655f13960093f57bb9baa2709891f330dd442

    auto& config2 = session.getAgentConfig();
    (*config2.sw()->ports())[0].description() = "Second version";
<<<<<<< HEAD
||||||| 8908ebf139
  // Call the actual rollback method without a revision (should go to previous)
  int newRevision = session.rollback(localhost());
=======
    session.setCommandLine(
        "config interface eth1/1/1 description Second version");
>>>>>>> c17655f13960093f57bb9baa2709891f330dd442
    session.saveConfig(
        cli::ServiceType::AGENT, cli::ConfigActionLevel::HITLESS);
    session.commit(localhost());
  }

  // Verify current content is "Second version"
  EXPECT_THAT(readFile(cliConfigPath), ::testing::HasSubstr("Second version"));

  // Rollback to previous commit (no argument)
  {
    TestableConfigSession session(
<<<<<<< HEAD
        sessionDir.string(), (getTestEtcDir() / "coop").string());
||||||| 8908ebf139
  // Verify r4 has same content as r2 (the previous revision)
  EXPECT_EQ(
      readFile(cliConfigDir / "agent-r2.conf"),
      readFile(cliConfigDir / "agent-r4.conf"));
=======
        sessionDir.string(), systemConfigDir_.string());
>>>>>>> c17655f13960093f57bb9baa2709891f330dd442

    std::string rollbackSha = session.rollback(localhost());

    // Verify rollback succeeded
    EXPECT_FALSE(rollbackSha.empty());

    // Verify content is now "First version" (from previous commit)
    EXPECT_THAT(readFile(cliConfigPath), ::testing::HasSubstr("First version"));
  }
}

TEST_F(ConfigSessionTestFixture, actionLevelDefaultIsHitless) {
<<<<<<< HEAD
  fs::path sessionDir = getTestHomeDir() / ".fboss2";
||||||| 8908ebf139
  fs::path sessionDir = getTestHomeDir() / ".fboss2";
  fs::path sessionConfig = sessionDir / "agent.conf";
=======
  fs::path sessionDir = testHomeDir_ / ".fboss2";
>>>>>>> c17655f13960093f57bb9baa2709891f330dd442

  // Create a ConfigSession
<<<<<<< HEAD
  TestableConfigSession session(
      sessionDir.string(), (getTestEtcDir() / "coop").string());
||||||| 8908ebf139
  TestableConfigSession session(
      sessionConfig.string(),
      getSystemConfigPath().string(),
      (getTestEtcDir() / "coop" / "cli").string());
=======
  TestableConfigSession session(sessionDir.string(), systemConfigDir_.string());
>>>>>>> c17655f13960093f57bb9baa2709891f330dd442

  // Default action level should be HITLESS
  EXPECT_EQ(
      session.getRequiredAction(cli::ServiceType::AGENT),
      cli::ConfigActionLevel::HITLESS);
}

TEST_F(ConfigSessionTestFixture, actionLevelUpdateAndGet) {
<<<<<<< HEAD
  fs::path sessionDir = getTestHomeDir() / ".fboss2";
||||||| 8908ebf139
  fs::path sessionDir = getTestHomeDir() / ".fboss2";
  fs::path sessionConfig = sessionDir / "agent.conf";
=======
  fs::path sessionDir = testHomeDir_ / ".fboss2";
>>>>>>> c17655f13960093f57bb9baa2709891f330dd442

  // Create a ConfigSession
<<<<<<< HEAD
  TestableConfigSession session(
      sessionDir.string(), (getTestEtcDir() / "coop").string());
||||||| 8908ebf139
  TestableConfigSession session(
      sessionConfig.string(),
      getSystemConfigPath().string(),
      (getTestEtcDir() / "coop" / "cli").string());
=======
  TestableConfigSession session(sessionDir.string(), systemConfigDir_.string());
>>>>>>> c17655f13960093f57bb9baa2709891f330dd442

  // Update to AGENT_RESTART
  session.updateRequiredAction(
      cli::ServiceType::AGENT, cli::ConfigActionLevel::AGENT_WARMBOOT);

  // Verify the action level was updated
  EXPECT_EQ(
      session.getRequiredAction(cli::ServiceType::AGENT),
      cli::ConfigActionLevel::AGENT_WARMBOOT);
}

TEST_F(ConfigSessionTestFixture, actionLevelHigherTakesPrecedence) {
<<<<<<< HEAD
  fs::path sessionDir = getTestHomeDir() / ".fboss2";
||||||| 8908ebf139
  fs::path sessionDir = getTestHomeDir() / ".fboss2";
  fs::path sessionConfig = sessionDir / "agent.conf";
=======
  fs::path sessionDir = testHomeDir_ / ".fboss2";
>>>>>>> c17655f13960093f57bb9baa2709891f330dd442

  // Create a ConfigSession
<<<<<<< HEAD
  TestableConfigSession session(
      sessionDir.string(), (getTestEtcDir() / "coop").string());
||||||| 8908ebf139
  TestableConfigSession session(
      sessionConfig.string(),
      getSystemConfigPath().string(),
      (getTestEtcDir() / "coop" / "cli").string());
=======
  TestableConfigSession session(sessionDir.string(), systemConfigDir_.string());
>>>>>>> c17655f13960093f57bb9baa2709891f330dd442

  // Update to AGENT_RESTART first
  session.updateRequiredAction(
      cli::ServiceType::AGENT, cli::ConfigActionLevel::AGENT_WARMBOOT);

  // Try to "downgrade" to HITLESS - should be ignored
  session.updateRequiredAction(
      cli::ServiceType::AGENT, cli::ConfigActionLevel::HITLESS);

  // Verify action level remains at AGENT_RESTART
  EXPECT_EQ(
      session.getRequiredAction(cli::ServiceType::AGENT),
      cli::ConfigActionLevel::AGENT_WARMBOOT);
}

TEST_F(ConfigSessionTestFixture, actionLevelReset) {
<<<<<<< HEAD
  fs::path sessionDir = getTestHomeDir() / ".fboss2";
||||||| 8908ebf139
  fs::path sessionDir = getTestHomeDir() / ".fboss2";
  fs::path sessionConfig = sessionDir / "agent.conf";
=======
  fs::path sessionDir = testHomeDir_ / ".fboss2";
>>>>>>> c17655f13960093f57bb9baa2709891f330dd442

  // Create a ConfigSession
<<<<<<< HEAD
  TestableConfigSession session(
      sessionDir.string(), (getTestEtcDir() / "coop").string());
||||||| 8908ebf139
  TestableConfigSession session(
      sessionConfig.string(),
      getSystemConfigPath().string(),
      (getTestEtcDir() / "coop" / "cli").string());
=======
  TestableConfigSession session(sessionDir.string(), systemConfigDir_.string());
>>>>>>> c17655f13960093f57bb9baa2709891f330dd442

  // Set to AGENT_RESTART
  session.updateRequiredAction(
      cli::ServiceType::AGENT, cli::ConfigActionLevel::AGENT_WARMBOOT);

  // Reset the action level
  session.resetRequiredAction(cli::ServiceType::AGENT);

  // Verify action level was reset to HITLESS
  EXPECT_EQ(
      session.getRequiredAction(cli::ServiceType::AGENT),
      cli::ConfigActionLevel::HITLESS);
}

TEST_F(ConfigSessionTestFixture, actionLevelPersistsToMetadataFile) {
<<<<<<< HEAD
  fs::path sessionDir = getTestHomeDir() / ".fboss2";
||||||| 8908ebf139
  fs::path sessionDir = getTestHomeDir() / ".fboss2";
  fs::path sessionConfig = sessionDir / "agent.conf";
  fs::path metadataFile = sessionDir / "conf_metadata.json";
=======
  fs::path sessionDir = testHomeDir_ / ".fboss2";
>>>>>>> c17655f13960093f57bb9baa2709891f330dd442
  fs::path metadataFile = sessionDir / "cli_metadata.json";

  // Create a ConfigSession and set action level via saveConfig
  {
    TestableConfigSession session(
<<<<<<< HEAD
        sessionDir.string(), (getTestEtcDir() / "coop").string());
||||||| 8908ebf139
        sessionConfig.string(),
        getSystemConfigPath().string(),
        (getTestEtcDir() / "coop" / "cli").string());
=======
        sessionDir.string(), systemConfigDir_.string());
>>>>>>> c17655f13960093f57bb9baa2709891f330dd442

    // Load the config (required before saveConfig)
    session.getAgentConfig();
    session.saveConfig(
        cli::ServiceType::AGENT, cli::ConfigActionLevel::AGENT_WARMBOOT);
  }

  // Verify metadata file exists and has correct JSON format
  EXPECT_TRUE(fs::exists(metadataFile));
  std::string content = readFile(metadataFile);

  // Parse the JSON and verify structure - uses symbolic enum names
  folly::dynamic json = folly::parseJson(content);
  EXPECT_TRUE(json.isObject());
  EXPECT_TRUE(json.count("action"));
  EXPECT_TRUE(json["action"].isObject());
  EXPECT_TRUE(json["action"].count("AGENT"));
  EXPECT_EQ(json["action"]["AGENT"].asString(), "AGENT_WARMBOOT");
}

TEST_F(ConfigSessionTestFixture, actionLevelLoadsFromMetadataFile) {
  fs::path sessionDir = testHomeDir_ / ".fboss2";
  fs::path sessionConfig = sessionDir / "agent.conf";
  fs::path metadataFile = sessionDir / "cli_metadata.json";
<<<<<<< HEAD
  fs::path cliConfigPath = getTestEtcDir() / "coop" / "cli" / "agent.conf";
||||||| 8908ebf139
  fs::path metadataFile = sessionDir / "conf_metadata.json";
=======
  fs::path cliConfigPath = systemConfigDir_ / "cli" / "agent.conf";
>>>>>>> c17655f13960093f57bb9baa2709891f330dd442

  // Create session directory and metadata file manually
  fs::create_directories(sessionDir);
  std::ofstream metaFile(metadataFile);
  // Use symbolic enum names for human readability
  metaFile << R"({"action":{"AGENT":"AGENT_WARMBOOT"}})";
  metaFile.close();

  // Also create the session config file (otherwise session will overwrite from
  // system)
  fs::copy_file(cliConfigPath, sessionConfig);

  // Create a ConfigSession - should load action level from metadata file
<<<<<<< HEAD
  TestableConfigSession session(
      sessionDir.string(), (getTestEtcDir() / "coop").string());
||||||| 8908ebf139
  TestableConfigSession session(
      sessionConfig.string(),
      getSystemConfigPath().string(),
      (getTestEtcDir() / "coop" / "cli").string());
=======
  TestableConfigSession session(sessionDir.string(), systemConfigDir_.string());
>>>>>>> c17655f13960093f57bb9baa2709891f330dd442

  // Verify action level was loaded
  EXPECT_EQ(
      session.getRequiredAction(cli::ServiceType::AGENT),
      cli::ConfigActionLevel::AGENT_WARMBOOT);
}

TEST_F(ConfigSessionTestFixture, actionLevelPersistsAcrossSessions) {
<<<<<<< HEAD
  fs::path sessionDir = getTestHomeDir() / ".fboss2";
||||||| 8908ebf139
  fs::path sessionDir = getTestHomeDir() / ".fboss2";
  fs::path sessionConfig = sessionDir / "agent.conf";
=======
  fs::path sessionDir = testHomeDir_ / ".fboss2";
>>>>>>> c17655f13960093f57bb9baa2709891f330dd442

  // First session: set action level via saveConfig
  {
    TestableConfigSession session1(
<<<<<<< HEAD
        sessionDir.string(), (getTestEtcDir() / "coop").string());
||||||| 8908ebf139
        sessionConfig.string(),
        getSystemConfigPath().string(),
        (getTestEtcDir() / "coop" / "cli").string());
=======
        sessionDir.string(), systemConfigDir_.string());
>>>>>>> c17655f13960093f57bb9baa2709891f330dd442

    // Load the config (required before saveConfig)
    session1.getAgentConfig();
    session1.saveConfig(
        cli::ServiceType::AGENT, cli::ConfigActionLevel::AGENT_WARMBOOT);
  }

  // Second session: verify action level was persisted
  {
    TestableConfigSession session2(
<<<<<<< HEAD
        sessionDir.string(), (getTestEtcDir() / "coop").string());
||||||| 8908ebf139
        sessionConfig.string(),
        getSystemConfigPath().string(),
        (getTestEtcDir() / "coop" / "cli").string());
=======
        sessionDir.string(), systemConfigDir_.string());
>>>>>>> c17655f13960093f57bb9baa2709891f330dd442

    EXPECT_EQ(
        session2.getRequiredAction(cli::ServiceType::AGENT),
        cli::ConfigActionLevel::AGENT_WARMBOOT);
  }
}

TEST_F(ConfigSessionTestFixture, commandTrackingBasic) {
<<<<<<< HEAD
  fs::path sessionDir = getTestHomeDir() / ".fboss2";
||||||| 8908ebf139
  fs::path sessionDir = getTestHomeDir() / ".fboss2";
  fs::path sessionConfig = sessionDir / "agent.conf";
  fs::path metadataFile = sessionDir / "conf_metadata.json";
=======
  fs::path sessionDir = testHomeDir_ / ".fboss2";
>>>>>>> c17655f13960093f57bb9baa2709891f330dd442
  fs::path metadataFile = sessionDir / "cli_metadata.json";

  // Create a ConfigSession, execute command, and verify persistence
  {
    TestableConfigSession session(
<<<<<<< HEAD
        sessionDir.string(), (getTestEtcDir() / "coop").string());
||||||| 8908ebf139
        sessionConfig.string(),
        getSystemConfigPath().string(),
        (getTestEtcDir() / "coop" / "cli").string());
=======
        sessionDir.string(), systemConfigDir_.string());
>>>>>>> c17655f13960093f57bb9baa2709891f330dd442

    // Initially, no commands should be recorded
    EXPECT_TRUE(session.getCommands().empty());

    // Simulate a command and save config
    session.addCommand("config interface eth1/1/1 description Test change");
    auto& config = session.getAgentConfig();
    auto& ports = *config.sw()->ports();
    ASSERT_FALSE(ports.empty());
    ports[0].description() = "Test change";
    session.saveConfig(
        cli::ServiceType::AGENT, cli::ConfigActionLevel::HITLESS);

    // Verify command was recorded in memory
    EXPECT_EQ(1, session.getCommands().size());
    EXPECT_EQ(
        "config interface eth1/1/1 description Test change",
        session.getCommands()[0]);
  }

  // Verify metadata file exists and has commands persisted
  EXPECT_TRUE(fs::exists(metadataFile));
  std::string content = readFile(metadataFile);

  // Parse the JSON and verify structure
  folly::dynamic json = folly::parseJson(content);
  EXPECT_TRUE(json.isObject());
  EXPECT_TRUE(json.count("commands"));
  EXPECT_TRUE(json["commands"].isArray());
  EXPECT_EQ(1, json["commands"].size());
  EXPECT_EQ(
      "config interface eth1/1/1 description Test change",
      json["commands"][0].asString());
}

TEST_F(ConfigSessionTestFixture, commandTrackingMultipleCommands) {
<<<<<<< HEAD
  fs::path sessionDir = getTestHomeDir() / ".fboss2";
||||||| 8908ebf139
  fs::path sessionDir = getTestHomeDir() / ".fboss2";
  fs::path sessionConfig = sessionDir / "agent.conf";
=======
  fs::path sessionDir = testHomeDir_ / ".fboss2";
>>>>>>> c17655f13960093f57bb9baa2709891f330dd442

  // Create a ConfigSession
<<<<<<< HEAD
  TestableConfigSession session(
      sessionDir.string(), (getTestEtcDir() / "coop").string());
||||||| 8908ebf139
  TestableConfigSession session(
      sessionConfig.string(),
      getSystemConfigPath().string(),
      (getTestEtcDir() / "coop" / "cli").string());
=======
  TestableConfigSession session(sessionDir.string(), systemConfigDir_.string());
>>>>>>> c17655f13960093f57bb9baa2709891f330dd442

  // Execute multiple commands
  auto& config = session.getAgentConfig();
  auto& ports = *config.sw()->ports();
  ASSERT_FALSE(ports.empty());

  session.addCommand("config interface eth1/1/1 mtu 9000");
  ports[0].description() = "First change";
  session.saveConfig(cli::ServiceType::AGENT, cli::ConfigActionLevel::HITLESS);

  session.addCommand("config interface eth1/1/1 description Test");
  ports[0].description() = "Second change";
  session.saveConfig(cli::ServiceType::AGENT, cli::ConfigActionLevel::HITLESS);

  session.addCommand("config interface eth1/1/1 speed 100G");
  ports[0].description() = "Third change";
  session.saveConfig(cli::ServiceType::AGENT, cli::ConfigActionLevel::HITLESS);

  // Verify all commands were recorded in order
  EXPECT_EQ(3, session.getCommands().size());
  EXPECT_EQ("config interface eth1/1/1 mtu 9000", session.getCommands()[0]);
  EXPECT_EQ(
      "config interface eth1/1/1 description Test", session.getCommands()[1]);
  EXPECT_EQ("config interface eth1/1/1 speed 100G", session.getCommands()[2]);
}

TEST_F(ConfigSessionTestFixture, commandTrackingPersistsAcrossSessions) {
<<<<<<< HEAD
  fs::path sessionDir = getTestHomeDir() / ".fboss2";
||||||| 8908ebf139
  fs::path sessionDir = getTestHomeDir() / ".fboss2";
  fs::path sessionConfig = sessionDir / "agent.conf";
=======
  fs::path sessionDir = testHomeDir_ / ".fboss2";
>>>>>>> c17655f13960093f57bb9baa2709891f330dd442

  // First session: execute some commands
  {
    TestableConfigSession session1(
<<<<<<< HEAD
        sessionDir.string(), (getTestEtcDir() / "coop").string());
||||||| 8908ebf139
        sessionConfig.string(),
        getSystemConfigPath().string(),
        (getTestEtcDir() / "coop" / "cli").string());
=======
        sessionDir.string(), systemConfigDir_.string());
>>>>>>> c17655f13960093f57bb9baa2709891f330dd442

    auto& config = session1.getAgentConfig();
    auto& ports = *config.sw()->ports();
    ASSERT_FALSE(ports.empty());

    session1.addCommand("config interface eth1/1/1 mtu 9000");
    ports[0].description() = "First change";
    session1.saveConfig(
        cli::ServiceType::AGENT, cli::ConfigActionLevel::HITLESS);

    session1.addCommand("config interface eth1/1/1 description Test");
    ports[0].description() = "Second change";
    session1.saveConfig(
        cli::ServiceType::AGENT, cli::ConfigActionLevel::HITLESS);
  }

  // Second session: verify commands were persisted
  {
    TestableConfigSession session2(
<<<<<<< HEAD
        sessionDir.string(), (getTestEtcDir() / "coop").string());
||||||| 8908ebf139
        sessionConfig.string(),
        getSystemConfigPath().string(),
        (getTestEtcDir() / "coop" / "cli").string());
=======
        sessionDir.string(), systemConfigDir_.string());
>>>>>>> c17655f13960093f57bb9baa2709891f330dd442

    EXPECT_EQ(2, session2.getCommands().size());
    EXPECT_EQ("config interface eth1/1/1 mtu 9000", session2.getCommands()[0]);
    EXPECT_EQ(
        "config interface eth1/1/1 description Test",
        session2.getCommands()[1]);
  }
}

TEST_F(ConfigSessionTestFixture, commandTrackingClearedOnReset) {
<<<<<<< HEAD
  fs::path sessionDir = getTestHomeDir() / ".fboss2";
||||||| 8908ebf139
  fs::path sessionDir = getTestHomeDir() / ".fboss2";
  fs::path sessionConfig = sessionDir / "agent.conf";
=======
  fs::path sessionDir = testHomeDir_ / ".fboss2";
>>>>>>> c17655f13960093f57bb9baa2709891f330dd442

  // Create a ConfigSession and add some commands
<<<<<<< HEAD
  TestableConfigSession session(
      sessionDir.string(), (getTestEtcDir() / "coop").string());
||||||| 8908ebf139
  TestableConfigSession session(
      sessionConfig.string(),
      getSystemConfigPath().string(),
      (getTestEtcDir() / "coop" / "cli").string());
=======
  TestableConfigSession session(sessionDir.string(), systemConfigDir_.string());
>>>>>>> c17655f13960093f57bb9baa2709891f330dd442

  auto& config = session.getAgentConfig();
  auto& ports = *config.sw()->ports();
  ASSERT_FALSE(ports.empty());

  session.addCommand("config interface eth1/1/1 mtu 9000");
  ports[0].description() = "Test change";
  session.saveConfig(cli::ServiceType::AGENT, cli::ConfigActionLevel::HITLESS);

  EXPECT_EQ(1, session.getCommands().size());

  // Reset the action level (which also clears commands)
  session.resetRequiredAction(cli::ServiceType::AGENT);

  // Verify commands were cleared
  EXPECT_TRUE(session.getCommands().empty());
}

TEST_F(ConfigSessionTestFixture, commandTrackingLoadsFromMetadataFile) {
  fs::path sessionDir = testHomeDir_ / ".fboss2";
  fs::path sessionConfig = sessionDir / "agent.conf";
  fs::path metadataFile = sessionDir / "cli_metadata.json";
<<<<<<< HEAD
  fs::path cliConfigPath = getTestEtcDir() / "coop" / "cli" / "agent.conf";
||||||| 8908ebf139
  fs::path metadataFile = sessionDir / "conf_metadata.json";
=======
  fs::path cliConfigPath = systemConfigDir_ / "cli" / "agent.conf";
>>>>>>> c17655f13960093f57bb9baa2709891f330dd442

  // Create session directory and metadata file manually
  fs::create_directories(sessionDir);
  std::ofstream metaFile(metadataFile);
  metaFile << R"({
    "action": {"AGENT": "HITLESS"},
    "commands": ["cmd1", "cmd2", "cmd3"]
  })";
  metaFile.close();

  // Also create the session config file
  fs::copy_file(cliConfigPath, sessionConfig);

  // Create a ConfigSession - should load commands from metadata file
<<<<<<< HEAD
  TestableConfigSession session(
      sessionDir.string(), (getTestEtcDir() / "coop").string());
||||||| 8908ebf139
  TestableConfigSession session(
      sessionConfig.string(),
      getSystemConfigPath().string(),
      (getTestEtcDir() / "coop" / "cli").string());
=======
  TestableConfigSession session(sessionDir.string(), systemConfigDir_.string());
>>>>>>> c17655f13960093f57bb9baa2709891f330dd442

  // Verify commands were loaded
  EXPECT_EQ(3, session.getCommands().size());
  EXPECT_EQ("cmd1", session.getCommands()[0]);
  EXPECT_EQ("cmd2", session.getCommands()[1]);
  EXPECT_EQ("cmd3", session.getCommands()[2]);
}

// Test that concurrent sessions are detected and rejected
// Scenario: user1 and user2 both start sessions based on the same commit,
// user1 commits first, then user2 tries to commit and should fail.
TEST_F(ConfigSessionTestFixture, concurrentSessionConflict) {
  fs::path sessionDir1 = getTestHomeDir() / ".fboss2_user1";
  fs::path sessionDir2 = getTestHomeDir() / ".fboss2_user2";

  // Setup mock agent server
  setupMockedAgentServer();
  // Only user1's commit should succeed, so only 1 reloadConfig call
  EXPECT_CALL(getMockAgent(), reloadConfig()).Times(1);

  // User1 creates a session (captures current HEAD as base)
  TestableConfigSession session1(
      sessionDir1.string(), (getTestEtcDir() / "coop").string());

  // User2 also creates a session at the same time (same base)
  TestableConfigSession session2(
      sessionDir2.string(), (getTestEtcDir() / "coop").string());

  // User1 makes a change and commits
  auto& config1 = session1.getAgentConfig();
  (*config1.sw()->ports())[0].description() = "User1 change";
  session1.saveConfig(cli::ServiceType::AGENT, cli::ConfigActionLevel::HITLESS);
  auto result1 = session1.commit(localhost());
  EXPECT_FALSE(result1.commitSha.empty());

  // User2 makes a different change
  auto& config2 = session2.getAgentConfig();
  (*config2.sw()->ports())[0].description() = "User2 change";
  session2.saveConfig(cli::ServiceType::AGENT, cli::ConfigActionLevel::HITLESS);

  // User2 tries to commit but should fail because user1 already committed
  EXPECT_THROW(
      {
        try {
          session2.commit(localhost());
        } catch (const std::runtime_error& e) {
          // Verify the error message mentions the conflict
          EXPECT_THAT(
              e.what(),
              ::testing::HasSubstr("system configuration has changed"));
          throw;
        }
      },
      std::runtime_error);

  // Verify that only user1's change is in the system config
  Git git((getTestEtcDir() / "coop").string());
  fs::path cliConfigPath = getTestEtcDir() / "coop" / "cli" / "agent.conf";
  std::string content;
  EXPECT_TRUE(folly::readFile(cliConfigPath.c_str(), content));
  EXPECT_THAT(content, ::testing::HasSubstr("User1 change"));
  EXPECT_THAT(content, ::testing::Not(::testing::HasSubstr("User2 change")));
}

TEST_F(ConfigSessionTestFixture, rebaseSuccessNoConflict) {
  // Test successful rebase when user2's changes don't conflict with user1's
  fs::path sessionDir1 = getTestHomeDir() / ".fboss2_user1";
  fs::path sessionDir2 = getTestHomeDir() / ".fboss2_user2";

  setupMockedAgentServer();
  EXPECT_CALL(getMockAgent(), reloadConfig()).Times(2);

  // User1 creates a session
  TestableConfigSession session1(
      sessionDir1.string(), (getTestEtcDir() / "coop").string());

  // User2 also creates a session at the same time (same base)
  TestableConfigSession session2(
      sessionDir2.string(), (getTestEtcDir() / "coop").string());

  // User1 changes port[0] description and commits
  auto& config1 = session1.getAgentConfig();
  (*config1.sw()->ports())[0].description() = "User1 change";
  session1.saveConfig(cli::ServiceType::AGENT, cli::ConfigActionLevel::HITLESS);
  auto result1 = session1.commit(localhost());
  EXPECT_FALSE(result1.commitSha.empty());

  // User2 changes port[1] description (non-conflicting - different port)
  auto& config2 = session2.getAgentConfig();
  ASSERT_GE(config2.sw()->ports()->size(), 2) << "Need at least 2 ports";
  (*config2.sw()->ports())[1].description() = "User2 change";
  session2.saveConfig(cli::ServiceType::AGENT, cli::ConfigActionLevel::HITLESS);

  // User2 tries to commit but fails due to stale base
  EXPECT_THROW(session2.commit(localhost()), std::runtime_error);

  // User2 rebases - should succeed since changes don't conflict
  EXPECT_NO_THROW(session2.rebase());

  // Now user2 can commit
  auto result2 = session2.commit(localhost());
  EXPECT_FALSE(result2.commitSha.empty());

  // Verify both changes are in the final config
  Git git((getTestEtcDir() / "coop").string());
  fs::path cliConfigPath = getTestEtcDir() / "coop" / "cli" / "agent.conf";
  std::string content;
  EXPECT_TRUE(folly::readFile(cliConfigPath.c_str(), content));
  EXPECT_THAT(content, ::testing::HasSubstr("User1 change"));
  EXPECT_THAT(content, ::testing::HasSubstr("User2 change"));
}

TEST_F(ConfigSessionTestFixture, rebaseFailsOnConflict) {
  // Test that rebase fails when user2's changes conflict with user1's
  fs::path sessionDir1 = getTestHomeDir() / ".fboss2_user1";
  fs::path sessionDir2 = getTestHomeDir() / ".fboss2_user2";

  setupMockedAgentServer();
  EXPECT_CALL(getMockAgent(), reloadConfig()).Times(1);

  // User1 creates a session
  TestableConfigSession session1(
      sessionDir1.string(), (getTestEtcDir() / "coop").string());

  // User2 also creates a session at the same time (same base)
  TestableConfigSession session2(
      sessionDir2.string(), (getTestEtcDir() / "coop").string());

  // User1 changes port[0] description to "User1 change"
  auto& config1 = session1.getAgentConfig();
  (*config1.sw()->ports())[0].description() = "User1 change";
  session1.saveConfig(cli::ServiceType::AGENT, cli::ConfigActionLevel::HITLESS);
  auto result1 = session1.commit(localhost());
  EXPECT_FALSE(result1.commitSha.empty());

  // User2 changes the SAME port[0] description to "User2 change" (conflict!)
  auto& config2 = session2.getAgentConfig();
  (*config2.sw()->ports())[0].description() = "User2 change";
  session2.saveConfig(cli::ServiceType::AGENT, cli::ConfigActionLevel::HITLESS);

  // User2 tries to rebase but should fail due to conflict
  EXPECT_THROW(
      {
        try {
          session2.rebase();
        } catch (const std::runtime_error& e) {
          EXPECT_THAT(e.what(), ::testing::HasSubstr("conflict"));
          throw;
        }
      },
      std::runtime_error);
}

TEST_F(ConfigSessionTestFixture, rebaseNotNeeded) {
  // Test that rebase throws when session is already up-to-date
  fs::path sessionDir = getTestHomeDir() / ".fboss2";

  setupMockedAgentServer();
  EXPECT_CALL(getMockAgent(), reloadConfig()).Times(0);

  TestableConfigSession session(
      sessionDir.string(), (getTestEtcDir() / "coop").string());

  // Make a change but don't commit yet
  auto& config = session.getAgentConfig();
  (*config.sw()->ports())[0].description() = "My change";
  session.saveConfig(cli::ServiceType::AGENT, cli::ConfigActionLevel::HITLESS);

  // Try to rebase - should fail because we're already on HEAD
  EXPECT_THROW(
      {
        try {
          session.rebase();
        } catch (const std::runtime_error& e) {
          EXPECT_THAT(e.what(), ::testing::HasSubstr("No rebase needed"));
          throw;
        }
      },
      std::runtime_error);
}

// Tests 3-way merge algorithm through rebase() covering:
// - Only session changed (head == base)
// - Only head changed (session == base)
// - Both changed to same value (no conflict)
// - Both changed to different values (conflict)
TEST_F(ConfigSessionTestFixture, threeWayMergeScenarios) {
  fs::path sessionDir1 = getTestHomeDir() / ".fboss2_user1";
  fs::path sessionDir2 = getTestHomeDir() / ".fboss2_user2";
  fs::path cliConfigPath = getTestEtcDir() / "coop" / "cli" / "agent.conf";

  setupMockedAgentServer();
  // 5 commits: 2 in scenario 1, 2 in scenario 2, 1 in scenario 3 (rebase fails)
  EXPECT_CALL(getMockAgent(), reloadConfig()).Times(5);

  // Scenario 1: Only session changed, head unchanged
  // User1 commits, User2 changes different field - should merge cleanly
  {
    TestableConfigSession session1(
        sessionDir1.string(), (getTestEtcDir() / "coop").string());
    TestableConfigSession session2(
        sessionDir2.string(), (getTestEtcDir() / "coop").string());

    (*session1.getAgentConfig().sw()->ports())[0].name() = "port0_renamed";
    session1.saveConfig(
        cli::ServiceType::AGENT, cli::ConfigActionLevel::HITLESS);
    session1.commit(localhost());

    (*session2.getAgentConfig().sw()->ports())[1].description() = "port1_desc";
    session2.saveConfig(
        cli::ServiceType::AGENT, cli::ConfigActionLevel::HITLESS);
    EXPECT_NO_THROW(session2.rebase());
    session2.commit(localhost());

    std::string content;
    EXPECT_TRUE(folly::readFile(cliConfigPath.c_str(), content));
    EXPECT_THAT(content, ::testing::HasSubstr("port0_renamed"));
    EXPECT_THAT(content, ::testing::HasSubstr("port1_desc"));
  }

  // Scenario 2: Both changed same field to identical value - no conflict
  {
    TestableConfigSession session1(
        sessionDir1.string(), (getTestEtcDir() / "coop").string());
    TestableConfigSession session2(
        sessionDir2.string(), (getTestEtcDir() / "coop").string());

    (*session1.getAgentConfig().sw()->ports())[0].description() = "same_value";
    session1.saveConfig(
        cli::ServiceType::AGENT, cli::ConfigActionLevel::HITLESS);
    session1.commit(localhost());

    (*session2.getAgentConfig().sw()->ports())[0].description() = "same_value";
    session2.saveConfig(
        cli::ServiceType::AGENT, cli::ConfigActionLevel::HITLESS);
    EXPECT_NO_THROW(session2.rebase());
    session2.commit(localhost());

    std::string content;
    EXPECT_TRUE(folly::readFile(cliConfigPath.c_str(), content));
    EXPECT_THAT(content, ::testing::HasSubstr("same_value"));
  }

  // Scenario 3: Both changed same field to different values - conflict
  {
    TestableConfigSession session1(
        sessionDir1.string(), (getTestEtcDir() / "coop").string());
    TestableConfigSession session2(
        sessionDir2.string(), (getTestEtcDir() / "coop").string());

    (*session1.getAgentConfig().sw()->ports())[0].description() = "user1_value";
    session1.saveConfig(
        cli::ServiceType::AGENT, cli::ConfigActionLevel::HITLESS);
    session1.commit(localhost());

    (*session2.getAgentConfig().sw()->ports())[0].description() = "user2_value";
    session2.saveConfig(
        cli::ServiceType::AGENT, cli::ConfigActionLevel::HITLESS);
    EXPECT_THROW(
        {
          try {
            session2.rebase();
          } catch (const std::runtime_error& e) {
            EXPECT_THAT(e.what(), ::testing::HasSubstr("conflict"));
            throw;
          }
        },
        std::runtime_error);
  }
}

} // namespace facebook::fboss
