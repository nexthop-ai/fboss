// (c) Meta Platforms, Inc. and affiliates. Confidential and proprietary.

#include <gtest/gtest.h>
#include <folly/FileUtil.h>
#include <folly/experimental/TestUtil.h>

#include "fboss/platform/weutil/FbossEepromInterface.h"

using EepromData = std::string;
using EepromContents = std::vector<std::pair<std::string, std::string>>;

namespace facebook::fboss::platform {

namespace {

// ONIE TlvInfo format test data
EepromData eepromOnie = {
    // Header: "TlvInfo\x00" + version(0x01) + total_length(0x0050 = 80 bytes)
    0x54, 0x6c, 0x76, 0x49, 0x6e, 0x66, 0x6f, 0x00, 0x01, 0x00, 0x50,
    // Product Name TLV (0x21, length=12, "TestProduct")
    0x21, 0x0c, 0x54, 0x65, 0x73, 0x74, 0x50, 0x72, 0x6f, 0x64, 0x75, 0x63, 0x74, 0x00,
    // Part Number TLV (0x22, length=8, "PN12345")
    0x22, 0x08, 0x50, 0x4e, 0x31, 0x32, 0x33, 0x34, 0x35, 0x00,
    // Serial Number TLV (0x23, length=10, "SN1234567")
    0x23, 0x0a, 0x53, 0x4e, 0x31, 0x32, 0x33, 0x34, 0x35, 0x36, 0x37, 0x00,
    // Base MAC Address TLV (0x24, length=6, 00:11:22:33:44:55)
    0x24, 0x06, 0x00, 0x11, 0x22, 0x33, 0x44, 0x55,
    // MAC Addresses TLV (0x2A, length=2, 256 addresses)
    0x2a, 0x02, 0x01, 0x00,
    // Manufacturer TLV (0x2B, length=8, "TestMfg")
    0x2b, 0x08, 0x54, 0x65, 0x73, 0x74, 0x4d, 0x66, 0x67, 0x00,
    // CRC-32 TLV (0xFE, length=4, placeholder CRC)
    0xfe, 0x04, 0x12, 0x34, 0x56, 0x78
};

EepromContents expectedContentsOnie = {
    {"Format", "ONIE TlvInfo"},
    {"Product Name", "TestProduct"},
    {"Part Number", "PN12345"},
    {"Serial Number", "SN1234567"},
    {"Base MAC Address", "00:11:22:33:44:55"},
    {"Manufacture Date", ""},
    {"Device Version", ""},
    {"Label Revision", ""},
    {"Platform Name", ""},
    {"ONIE Version", ""},
    {"MAC Addresses", "256"},
    {"Manufacturer", "TestMfg"},
    {"Manufacture Country", ""},
    {"Vendor Name", ""},
    {"Diag Version", ""},
    {"Service Tag", ""},
    {"Vendor Extension", ""},
    {"CRC-32", "0x12345678 (CRC Mismatch. Expected 0x6B9A8F2C)"},
};

// Real device ONIE EEPROM data from Nexthop NH-4010
EepromData eepromOnieReal = {
    // Header: "TlvInfo\x00" + version(0x01) + total_length(0x006d = 109 bytes)
    0x54, 0x6c, 0x76, 0x49, 0x6e, 0x66, 0x6f, 0x00, 0x01, 0x00, 0x6d,
    // Product Name TLV (0x21, length=7, "NH-4010")
    0x21, 0x07, 0x4e, 0x48, 0x2d, 0x34, 0x30, 0x31, 0x30,
    // Part Number TLV (0x22, length=12, "722-00002-02")
    0x22, 0x0c, 0x37, 0x32, 0x32, 0x2d, 0x30, 0x30, 0x30, 0x30, 0x32, 0x2d, 0x30, 0x32,
    // Serial Number TLV (0x23, length=14, "NH-FSJ25150012")
    0x23, 0x0e, 0x4e, 0x48, 0x2d, 0x46, 0x53, 0x4a, 0x32, 0x35, 0x31, 0x35, 0x30, 0x30, 0x31, 0x32,
    // Base MAC Address TLV (0x24, length=6, E8:E4:9D:00:18:28)
    0x24, 0x06, 0xe8, 0xe4, 0x9d, 0x00, 0x18, 0x28,
    // Device Version TLV (0x26, length=1, 1)
    0x26, 0x01, 0x01,
    // Label Revision TLV (0x27, length=2, "P1")
    0x27, 0x02, 0x50, 0x31,
    // Platform Name TLV (0x28, length=22, "x86_64-nexthop_4010-r0")
    0x28, 0x16, 0x78, 0x38, 0x36, 0x5f, 0x36, 0x34, 0x2d, 0x6e, 0x65, 0x78, 0x74, 0x68, 0x6f, 0x70, 0x5f, 0x34, 0x30, 0x31, 0x30, 0x2d, 0x72, 0x30,
    // Manufacturer TLV (0x2B, length=7, "Nexthop")
    0x2b, 0x07, 0x4e, 0x65, 0x78, 0x74, 0x68, 0x6f, 0x70,
    // Service Tag TLV (0x2F, length=14, "www.nexthop.ai")
    0x2f, 0x0e, 0x77, 0x77, 0x77, 0x2e, 0x6e, 0x65, 0x78, 0x74, 0x68, 0x6f, 0x70, 0x2e, 0x61, 0x69,
    // CRC-32 TLV (0xFE, length=4, 0xF2614683)
    0xfe, 0x04, 0xf2, 0x61, 0x46, 0x83
};

EepromContents expectedContentsOnieReal = {
    {"Format", "ONIE TlvInfo"},
    {"Product Name", "NH-4010"},
    {"Part Number", "722-00002-02"},
    {"Serial Number", "NH-FSJ25150012"},
    {"Base MAC Address", "e8:e4:9d:00:18:28"},
    {"Manufacture Date", ""},
    {"Device Version", "1"},
    {"Label Revision", "P1"},
    {"Platform Name", "x86_64-nexthop_4010-r0"},
    {"ONIE Version", ""},
    {"MAC Addresses", ""},
    {"Manufacturer", "Nexthop"},
    {"Manufacture Country", ""},
    {"Vendor Name", ""},
    {"Diag Version", ""},
    {"Service Tag", "www.nexthop.ai"},
    {"Vendor Extension", ""},
    {"CRC-32", "0xf2614683 (CRC Matched)"},
};

std::vector<std::pair<EepromData, EepromContents>> OnieEepromTestInfo = {
    {eepromOnie, expectedContentsOnie},
    {eepromOnieReal, expectedContentsOnieReal},
};

} // namespace

TEST(FbossEepromOnieTest, OnieFormat) {
  for (auto& [eepromData, expectedContents] : OnieEepromTestInfo) {
    folly::test::TemporaryDirectory tmpDir = folly::test::TemporaryDirectory();
    std::string fileName = tmpDir.path().string() + "/eepromContent";
    folly::writeFile(eepromData, fileName.c_str());
    FbossEepromInterface interface(fileName, 0);
    auto parsedContents = interface.getContents();
    ASSERT_EQ(expectedContents.size(), parsedContents.size());
    for (size_t i = 0; i < expectedContents.size(); i++) {
      EXPECT_EQ(parsedContents[i], expectedContents[i]);
    }
  }
}

TEST(FbossEepromOnieTest, OnieRealDevice) {
  // Test specifically with the real Nexthop NH-4010 device data
  folly::test::TemporaryDirectory tmpDir = folly::test::TemporaryDirectory();
  std::string fileName = tmpDir.path().string() + "/eepromContent";
  folly::writeFile(eepromOnieReal, fileName.c_str());
  FbossEepromInterface interface(fileName, 0);
  auto parsedContents = interface.getContents();

  // Verify format is detected as ONIE
  EXPECT_EQ(parsedContents[0].first, "Format");
  EXPECT_EQ(parsedContents[0].second, "ONIE TlvInfo");

  // Verify specific fields from the real device
  std::map<std::string, std::string> contentsMap;
  for (const auto& [key, value] : parsedContents) {
    contentsMap[key] = value;
  }

  EXPECT_EQ(contentsMap["Product Name"], "NH-4010");
  EXPECT_EQ(contentsMap["Part Number"], "722-00002-02");
  EXPECT_EQ(contentsMap["Serial Number"], "NH-FSJ25150012");
  EXPECT_EQ(contentsMap["Base MAC Address"], "e8:e4:9d:00:18:28");
  EXPECT_EQ(contentsMap["Device Version"], "1");
  EXPECT_EQ(contentsMap["Label Revision"], "P1");
  EXPECT_EQ(contentsMap["Platform Name"], "x86_64-nexthop_4010-r0");
  EXPECT_EQ(contentsMap["Manufacturer"], "Nexthop");
  EXPECT_EQ(contentsMap["Service Tag"], "www.nexthop.ai");
  EXPECT_EQ(contentsMap["CRC-32"], "0xf2614683 (CRC Matched)");
}

} // namespace facebook::fboss::platform
