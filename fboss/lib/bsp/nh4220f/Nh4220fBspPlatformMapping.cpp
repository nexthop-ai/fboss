// (c) Nexthop Systems, Inc. and affiliates. Confidential and proprietary.

#include "fboss/lib/bsp/nh4220f/Nh4220fBspPlatformMapping.h"
#include <thrift/lib/cpp2/protocol/Serializer.h>
#include "fboss/lib/bsp/BspPlatformMapping.h"
#include "fboss/lib/bsp/gen-cpp2/bsp_platform_mapping_types.h"

using namespace facebook::fboss;
using namespace apache::thrift;

namespace {
constexpr auto kJsonBspPlatformMappingStr = R"(
{
  "pimMapping": {
    "1": {
      "pimID": 1,
      "tcvrMapping": {
        "1": {
          "tcvrId": 1,
          "accessControl": {
            "controllerId": "1",
            "type": 1,
            "reset": {
              "sysfsPath": "/run/devmap/xcvrs/xcvr_ctrl_1/xcvr_reset_1",
              "mask": 1,
              "gpioOffset": 0,
              "resetHoldHi": 0
            },
            "presence": {
              "sysfsPath": "/run/devmap/xcvrs/xcvr_ctrl_1/xcvr_present_1",
              "mask": 1,
              "gpioOffset": 0,
              "presentHoldHi": 0
            },
            "gpioChip": ""
          },
          "io": {
            "controllerId": "1",
            "type": 1,
            "devicePath": "/run/devmap/xcvrs/xcvr_io_1"
            },
            "tcvrLaneToLedId": {"1": 1, "2": 1, "3": 1, "4": 1, "5": 1, "6": 1, "7": 1, "8": 1}        },
        "2": {
          "tcvrId": 2,
          "accessControl": {
            "controllerId": "2",
            "type": 1,
            "reset": {
              "sysfsPath": "/run/devmap/xcvrs/xcvr_ctrl_2/xcvr_reset_2",
              "mask": 1,
              "gpioOffset": 0,
              "resetHoldHi": 0
            },
            "presence": {
              "sysfsPath": "/run/devmap/xcvrs/xcvr_ctrl_2/xcvr_present_2",
              "mask": 1,
              "gpioOffset": 0,
              "presentHoldHi": 0
            },
            "gpioChip": ""
          },
          "io": {
            "controllerId": "2",
            "type": 1,
            "devicePath": "/run/devmap/xcvrs/xcvr_io_2"
            },
            "tcvrLaneToLedId": {"1": 2, "2": 2, "3": 2, "4": 2, "5": 2, "6": 2, "7": 2, "8": 2}        },
        "3": {
          "tcvrId": 3,
          "accessControl": {
            "controllerId": "3",
            "type": 1,
            "reset": {
              "sysfsPath": "/run/devmap/xcvrs/xcvr_ctrl_3/xcvr_reset_3",
              "mask": 1,
              "gpioOffset": 0,
              "resetHoldHi": 0
            },
            "presence": {
              "sysfsPath": "/run/devmap/xcvrs/xcvr_ctrl_3/xcvr_present_3",
              "mask": 1,
              "gpioOffset": 0,
              "presentHoldHi": 0
            },
            "gpioChip": ""
          },
          "io": {
            "controllerId": "3",
            "type": 1,
            "devicePath": "/run/devmap/xcvrs/xcvr_io_3"
            },
            "tcvrLaneToLedId": {"1": 3, "2": 3, "3": 3, "4": 3, "5": 3, "6": 3, "7": 3, "8": 3}        },
        "4": {
          "tcvrId": 4,
          "accessControl": {
            "controllerId": "4",
            "type": 1,
            "reset": {
              "sysfsPath": "/run/devmap/xcvrs/xcvr_ctrl_4/xcvr_reset_4",
              "mask": 1,
              "gpioOffset": 0,
              "resetHoldHi": 0
            },
            "presence": {
              "sysfsPath": "/run/devmap/xcvrs/xcvr_ctrl_4/xcvr_present_4",
              "mask": 1,
              "gpioOffset": 0,
              "presentHoldHi": 0
            },
            "gpioChip": ""
          },
          "io": {
            "controllerId": "4",
            "type": 1,
            "devicePath": "/run/devmap/xcvrs/xcvr_io_4"
            },
            "tcvrLaneToLedId": {"1": 4, "2": 4, "3": 4, "4": 4, "5": 4, "6": 4, "7": 4, "8": 4}        },
        "5": {
          "tcvrId": 5,
          "accessControl": {
            "controllerId": "5",
            "type": 1,
            "reset": {
              "sysfsPath": "/run/devmap/xcvrs/xcvr_ctrl_5/xcvr_reset_5",
              "mask": 1,
              "gpioOffset": 0,
              "resetHoldHi": 0
            },
            "presence": {
              "sysfsPath": "/run/devmap/xcvrs/xcvr_ctrl_5/xcvr_present_5",
              "mask": 1,
              "gpioOffset": 0,
              "presentHoldHi": 0
            },
            "gpioChip": ""
          },
          "io": {
            "controllerId": "5",
            "type": 1,
            "devicePath": "/run/devmap/xcvrs/xcvr_io_5"
            },
            "tcvrLaneToLedId": {"1": 5, "2": 5, "3": 5, "4": 5, "5": 5, "6": 5, "7": 5, "8": 5}        },
        "6": {
          "tcvrId": 6,
          "accessControl": {
            "controllerId": "6",
            "type": 1,
            "reset": {
              "sysfsPath": "/run/devmap/xcvrs/xcvr_ctrl_6/xcvr_reset_6",
              "mask": 1,
              "gpioOffset": 0,
              "resetHoldHi": 0
            },
            "presence": {
              "sysfsPath": "/run/devmap/xcvrs/xcvr_ctrl_6/xcvr_present_6",
              "mask": 1,
              "gpioOffset": 0,
              "presentHoldHi": 0
            },
            "gpioChip": ""
          },
          "io": {
            "controllerId": "6",
            "type": 1,
            "devicePath": "/run/devmap/xcvrs/xcvr_io_6"
            },
            "tcvrLaneToLedId": {"1": 6, "2": 6, "3": 6, "4": 6, "5": 6, "6": 6, "7": 6, "8": 6}        },
        "7": {
          "tcvrId": 7,
          "accessControl": {
            "controllerId": "7",
            "type": 1,
            "reset": {
              "sysfsPath": "/run/devmap/xcvrs/xcvr_ctrl_7/xcvr_reset_7",
              "mask": 1,
              "gpioOffset": 0,
              "resetHoldHi": 0
            },
            "presence": {
              "sysfsPath": "/run/devmap/xcvrs/xcvr_ctrl_7/xcvr_present_7",
              "mask": 1,
              "gpioOffset": 0,
              "presentHoldHi": 0
            },
            "gpioChip": ""
          },
          "io": {
            "controllerId": "7",
            "type": 1,
            "devicePath": "/run/devmap/xcvrs/xcvr_io_7"
            },
            "tcvrLaneToLedId": {"1": 7, "2": 7, "3": 7, "4": 7, "5": 7, "6": 7, "7": 7, "8": 7}        },
        "8": {
          "tcvrId": 8,
          "accessControl": {
            "controllerId": "8",
            "type": 1,
            "reset": {
              "sysfsPath": "/run/devmap/xcvrs/xcvr_ctrl_8/xcvr_reset_8",
              "mask": 1,
              "gpioOffset": 0,
              "resetHoldHi": 0
            },
            "presence": {
              "sysfsPath": "/run/devmap/xcvrs/xcvr_ctrl_8/xcvr_present_8",
              "mask": 1,
              "gpioOffset": 0,
              "presentHoldHi": 0
            },
            "gpioChip": ""
          },
          "io": {
            "controllerId": "8",
            "type": 1,
            "devicePath": "/run/devmap/xcvrs/xcvr_io_8"
            },
            "tcvrLaneToLedId": {"1": 8, "2": 8, "3": 8, "4": 8, "5": 8, "6": 8, "7": 8, "8": 8}        },
        "9": {
          "tcvrId": 9,
          "accessControl": {
            "controllerId": "9",
            "type": 1,
            "reset": {
              "sysfsPath": "/run/devmap/xcvrs/xcvr_ctrl_9/xcvr_reset_9",
              "mask": 1,
              "gpioOffset": 0,
              "resetHoldHi": 0
            },
            "presence": {
              "sysfsPath": "/run/devmap/xcvrs/xcvr_ctrl_9/xcvr_present_9",
              "mask": 1,
              "gpioOffset": 0,
              "presentHoldHi": 0
            },
            "gpioChip": ""
          },
          "io": {
            "controllerId": "9",
            "type": 1,
            "devicePath": "/run/devmap/xcvrs/xcvr_io_9"
            },
            "tcvrLaneToLedId": {"1": 9, "2": 9, "3": 9, "4": 9, "5": 9, "6": 9, "7": 9, "8": 9}        },
        "10": {
          "tcvrId": 10,
          "accessControl": {
            "controllerId": "10",
            "type": 1,
            "reset": {
              "sysfsPath": "/run/devmap/xcvrs/xcvr_ctrl_10/xcvr_reset_10",
              "mask": 1,
              "gpioOffset": 0,
              "resetHoldHi": 0
            },
            "presence": {
              "sysfsPath": "/run/devmap/xcvrs/xcvr_ctrl_10/xcvr_present_10",
              "mask": 1,
              "gpioOffset": 0,
              "presentHoldHi": 0
            },
            "gpioChip": ""
          },
          "io": {
            "controllerId": "10",
            "type": 1,
            "devicePath": "/run/devmap/xcvrs/xcvr_io_10"
            },
            "tcvrLaneToLedId": {"1": 10, "2": 10, "3": 10, "4": 10, "5": 10, "6": 10, "7": 10, "8": 10}        },
        "11": {
          "tcvrId": 11,
          "accessControl": {
            "controllerId": "11",
            "type": 1,
            "reset": {
              "sysfsPath": "/run/devmap/xcvrs/xcvr_ctrl_11/xcvr_reset_11",
              "mask": 1,
              "gpioOffset": 0,
              "resetHoldHi": 0
            },
            "presence": {
              "sysfsPath": "/run/devmap/xcvrs/xcvr_ctrl_11/xcvr_present_11",
              "mask": 1,
              "gpioOffset": 0,
              "presentHoldHi": 0
            },
            "gpioChip": ""
          },
          "io": {
            "controllerId": "11",
            "type": 1,
            "devicePath": "/run/devmap/xcvrs/xcvr_io_11"
            },
            "tcvrLaneToLedId": {"1": 11, "2": 11, "3": 11, "4": 11, "5": 11, "6": 11, "7": 11, "8": 11}        },
        "12": {
          "tcvrId": 12,
          "accessControl": {
            "controllerId": "12",
            "type": 1,
            "reset": {
              "sysfsPath": "/run/devmap/xcvrs/xcvr_ctrl_12/xcvr_reset_12",
              "mask": 1,
              "gpioOffset": 0,
              "resetHoldHi": 0
            },
            "presence": {
              "sysfsPath": "/run/devmap/xcvrs/xcvr_ctrl_12/xcvr_present_12",
              "mask": 1,
              "gpioOffset": 0,
              "presentHoldHi": 0
            },
            "gpioChip": ""
          },
          "io": {
            "controllerId": "12",
            "type": 1,
            "devicePath": "/run/devmap/xcvrs/xcvr_io_12"
            },
            "tcvrLaneToLedId": {"1": 12, "2": 12, "3": 12, "4": 12, "5": 12, "6": 12, "7": 12, "8": 12}        },
        "13": {
          "tcvrId": 13,
          "accessControl": {
            "controllerId": "13",
            "type": 1,
            "reset": {
              "sysfsPath": "/run/devmap/xcvrs/xcvr_ctrl_13/xcvr_reset_13",
              "mask": 1,
              "gpioOffset": 0,
              "resetHoldHi": 0
            },
            "presence": {
              "sysfsPath": "/run/devmap/xcvrs/xcvr_ctrl_13/xcvr_present_13",
              "mask": 1,
              "gpioOffset": 0,
              "presentHoldHi": 0
            },
            "gpioChip": ""
          },
          "io": {
            "controllerId": "13",
            "type": 1,
            "devicePath": "/run/devmap/xcvrs/xcvr_io_13"
            },
            "tcvrLaneToLedId": {"1": 13, "2": 13, "3": 13, "4": 13, "5": 13, "6": 13, "7": 13, "8": 13}        },
        "14": {
          "tcvrId": 14,
          "accessControl": {
            "controllerId": "14",
            "type": 1,
            "reset": {
              "sysfsPath": "/run/devmap/xcvrs/xcvr_ctrl_14/xcvr_reset_14",
              "mask": 1,
              "gpioOffset": 0,
              "resetHoldHi": 0
            },
            "presence": {
              "sysfsPath": "/run/devmap/xcvrs/xcvr_ctrl_14/xcvr_present_14",
              "mask": 1,
              "gpioOffset": 0,
              "presentHoldHi": 0
            },
            "gpioChip": ""
          },
          "io": {
            "controllerId": "14",
            "type": 1,
            "devicePath": "/run/devmap/xcvrs/xcvr_io_14"
            },
            "tcvrLaneToLedId": {"1": 14, "2": 14, "3": 14, "4": 14, "5": 14, "6": 14, "7": 14, "8": 14}        },
        "15": {
          "tcvrId": 15,
          "accessControl": {
            "controllerId": "15",
            "type": 1,
            "reset": {
              "sysfsPath": "/run/devmap/xcvrs/xcvr_ctrl_15/xcvr_reset_15",
              "mask": 1,
              "gpioOffset": 0,
              "resetHoldHi": 0
            },
            "presence": {
              "sysfsPath": "/run/devmap/xcvrs/xcvr_ctrl_15/xcvr_present_15",
              "mask": 1,
              "gpioOffset": 0,
              "presentHoldHi": 0
            },
            "gpioChip": ""
          },
          "io": {
            "controllerId": "15",
            "type": 1,
            "devicePath": "/run/devmap/xcvrs/xcvr_io_15"
            },
            "tcvrLaneToLedId": {"1": 15, "2": 15, "3": 15, "4": 15, "5": 15, "6": 15, "7": 15, "8": 15}        },
        "16": {
          "tcvrId": 16,
          "accessControl": {
            "controllerId": "16",
            "type": 1,
            "reset": {
              "sysfsPath": "/run/devmap/xcvrs/xcvr_ctrl_16/xcvr_reset_16",
              "mask": 1,
              "gpioOffset": 0,
              "resetHoldHi": 0
            },
            "presence": {
              "sysfsPath": "/run/devmap/xcvrs/xcvr_ctrl_16/xcvr_present_16",
              "mask": 1,
              "gpioOffset": 0,
              "presentHoldHi": 0
            },
            "gpioChip": ""
          },
          "io": {
            "controllerId": "16",
            "type": 1,
            "devicePath": "/run/devmap/xcvrs/xcvr_io_16"
            },
            "tcvrLaneToLedId": {"1": 16, "2": 16, "3": 16, "4": 16, "5": 16, "6": 16, "7": 16, "8": 16}        },
        "17": {
          "tcvrId": 17,
          "accessControl": {
            "controllerId": "17",
            "type": 1,
            "reset": {
              "sysfsPath": "/run/devmap/xcvrs/xcvr_ctrl_17/xcvr_reset_17",
              "mask": 1,
              "gpioOffset": 0,
              "resetHoldHi": 0
            },
            "presence": {
              "sysfsPath": "/run/devmap/xcvrs/xcvr_ctrl_17/xcvr_present_17",
              "mask": 1,
              "gpioOffset": 0,
              "presentHoldHi": 0
            },
            "gpioChip": ""
          },
          "io": {
            "controllerId": "17",
            "type": 1,
            "devicePath": "/run/devmap/xcvrs/xcvr_io_17"
            },
            "tcvrLaneToLedId": {"1": 17, "2": 17, "3": 17, "4": 17, "5": 17, "6": 17, "7": 17, "8": 17}        },
        "18": {
          "tcvrId": 18,
          "accessControl": {
            "controllerId": "18",
            "type": 1,
            "reset": {
              "sysfsPath": "/run/devmap/xcvrs/xcvr_ctrl_18/xcvr_reset_18",
              "mask": 1,
              "gpioOffset": 0,
              "resetHoldHi": 0
            },
            "presence": {
              "sysfsPath": "/run/devmap/xcvrs/xcvr_ctrl_18/xcvr_present_18",
              "mask": 1,
              "gpioOffset": 0,
              "presentHoldHi": 0
            },
            "gpioChip": ""
          },
          "io": {
            "controllerId": "18",
            "type": 1,
            "devicePath": "/run/devmap/xcvrs/xcvr_io_18"
            },
            "tcvrLaneToLedId": {"1": 18, "2": 18, "3": 18, "4": 18, "5": 18, "6": 18, "7": 18, "8": 18}        },
        "19": {
          "tcvrId": 19,
          "accessControl": {
            "controllerId": "19",
            "type": 1,
            "reset": {
              "sysfsPath": "/run/devmap/xcvrs/xcvr_ctrl_19/xcvr_reset_19",
              "mask": 1,
              "gpioOffset": 0,
              "resetHoldHi": 0
            },
            "presence": {
              "sysfsPath": "/run/devmap/xcvrs/xcvr_ctrl_19/xcvr_present_19",
              "mask": 1,
              "gpioOffset": 0,
              "presentHoldHi": 0
            },
            "gpioChip": ""
          },
          "io": {
            "controllerId": "19",
            "type": 1,
            "devicePath": "/run/devmap/xcvrs/xcvr_io_19"
            },
            "tcvrLaneToLedId": {"1": 19, "2": 19, "3": 19, "4": 19, "5": 19, "6": 19, "7": 19, "8": 19}        },
        "20": {
          "tcvrId": 20,
          "accessControl": {
            "controllerId": "20",
            "type": 1,
            "reset": {
              "sysfsPath": "/run/devmap/xcvrs/xcvr_ctrl_20/xcvr_reset_20",
              "mask": 1,
              "gpioOffset": 0,
              "resetHoldHi": 0
            },
            "presence": {
              "sysfsPath": "/run/devmap/xcvrs/xcvr_ctrl_20/xcvr_present_20",
              "mask": 1,
              "gpioOffset": 0,
              "presentHoldHi": 0
            },
            "gpioChip": ""
          },
          "io": {
            "controllerId": "20",
            "type": 1,
            "devicePath": "/run/devmap/xcvrs/xcvr_io_20"
            },
            "tcvrLaneToLedId": {"1": 20, "2": 20, "3": 20, "4": 20, "5": 20, "6": 20, "7": 20, "8": 20}        },
        "21": {
          "tcvrId": 21,
          "accessControl": {
            "controllerId": "21",
            "type": 1,
            "reset": {
              "sysfsPath": "/run/devmap/xcvrs/xcvr_ctrl_21/xcvr_reset_21",
              "mask": 1,
              "gpioOffset": 0,
              "resetHoldHi": 0
            },
            "presence": {
              "sysfsPath": "/run/devmap/xcvrs/xcvr_ctrl_21/xcvr_present_21",
              "mask": 1,
              "gpioOffset": 0,
              "presentHoldHi": 0
            },
            "gpioChip": ""
          },
          "io": {
            "controllerId": "21",
            "type": 1,
            "devicePath": "/run/devmap/xcvrs/xcvr_io_21"
            },
            "tcvrLaneToLedId": {"1": 21, "2": 21, "3": 21, "4": 21, "5": 21, "6": 21, "7": 21, "8": 21}        },
        "22": {
          "tcvrId": 22,
          "accessControl": {
            "controllerId": "22",
            "type": 1,
            "reset": {
              "sysfsPath": "/run/devmap/xcvrs/xcvr_ctrl_22/xcvr_reset_22",
              "mask": 1,
              "gpioOffset": 0,
              "resetHoldHi": 0
            },
            "presence": {
              "sysfsPath": "/run/devmap/xcvrs/xcvr_ctrl_22/xcvr_present_22",
              "mask": 1,
              "gpioOffset": 0,
              "presentHoldHi": 0
            },
            "gpioChip": ""
          },
          "io": {
            "controllerId": "22",
            "type": 1,
            "devicePath": "/run/devmap/xcvrs/xcvr_io_22"
            },
            "tcvrLaneToLedId": {"1": 22, "2": 22, "3": 22, "4": 22, "5": 22, "6": 22, "7": 22, "8": 22}        },
        "23": {
          "tcvrId": 23,
          "accessControl": {
            "controllerId": "23",
            "type": 1,
            "reset": {
              "sysfsPath": "/run/devmap/xcvrs/xcvr_ctrl_23/xcvr_reset_23",
              "mask": 1,
              "gpioOffset": 0,
              "resetHoldHi": 0
            },
            "presence": {
              "sysfsPath": "/run/devmap/xcvrs/xcvr_ctrl_23/xcvr_present_23",
              "mask": 1,
              "gpioOffset": 0,
              "presentHoldHi": 0
            },
            "gpioChip": ""
          },
          "io": {
            "controllerId": "23",
            "type": 1,
            "devicePath": "/run/devmap/xcvrs/xcvr_io_23"
            },
            "tcvrLaneToLedId": {"1": 23, "2": 23, "3": 23, "4": 23, "5": 23, "6": 23, "7": 23, "8": 23}        },
        "24": {
          "tcvrId": 24,
          "accessControl": {
            "controllerId": "24",
            "type": 1,
            "reset": {
              "sysfsPath": "/run/devmap/xcvrs/xcvr_ctrl_24/xcvr_reset_24",
              "mask": 1,
              "gpioOffset": 0,
              "resetHoldHi": 0
            },
            "presence": {
              "sysfsPath": "/run/devmap/xcvrs/xcvr_ctrl_24/xcvr_present_24",
              "mask": 1,
              "gpioOffset": 0,
              "presentHoldHi": 0
            },
            "gpioChip": ""
          },
          "io": {
            "controllerId": "24",
            "type": 1,
            "devicePath": "/run/devmap/xcvrs/xcvr_io_24"
            },
            "tcvrLaneToLedId": {"1": 24, "2": 24, "3": 24, "4": 24, "5": 24, "6": 24, "7": 24, "8": 24}        },
        "25": {
          "tcvrId": 25,
          "accessControl": {
            "controllerId": "25",
            "type": 1,
            "reset": {
              "sysfsPath": "/run/devmap/xcvrs/xcvr_ctrl_25/xcvr_reset_25",
              "mask": 1,
              "gpioOffset": 0,
              "resetHoldHi": 0
            },
            "presence": {
              "sysfsPath": "/run/devmap/xcvrs/xcvr_ctrl_25/xcvr_present_25",
              "mask": 1,
              "gpioOffset": 0,
              "presentHoldHi": 0
            },
            "gpioChip": ""
          },
          "io": {
            "controllerId": "25",
            "type": 1,
            "devicePath": "/run/devmap/xcvrs/xcvr_io_25"
            },
            "tcvrLaneToLedId": {"1": 25, "2": 25, "3": 25, "4": 25, "5": 25, "6": 25, "7": 25, "8": 25}        },
        "26": {
          "tcvrId": 26,
          "accessControl": {
            "controllerId": "26",
            "type": 1,
            "reset": {
              "sysfsPath": "/run/devmap/xcvrs/xcvr_ctrl_26/xcvr_reset_26",
              "mask": 1,
              "gpioOffset": 0,
              "resetHoldHi": 0
            },
            "presence": {
              "sysfsPath": "/run/devmap/xcvrs/xcvr_ctrl_26/xcvr_present_26",
              "mask": 1,
              "gpioOffset": 0,
              "presentHoldHi": 0
            },
            "gpioChip": ""
          },
          "io": {
            "controllerId": "26",
            "type": 1,
            "devicePath": "/run/devmap/xcvrs/xcvr_io_26"
            },
            "tcvrLaneToLedId": {"1": 26, "2": 26, "3": 26, "4": 26, "5": 26, "6": 26, "7": 26, "8": 26}        },
        "27": {
          "tcvrId": 27,
          "accessControl": {
            "controllerId": "27",
            "type": 1,
            "reset": {
              "sysfsPath": "/run/devmap/xcvrs/xcvr_ctrl_27/xcvr_reset_27",
              "mask": 1,
              "gpioOffset": 0,
              "resetHoldHi": 0
            },
            "presence": {
              "sysfsPath": "/run/devmap/xcvrs/xcvr_ctrl_27/xcvr_present_27",
              "mask": 1,
              "gpioOffset": 0,
              "presentHoldHi": 0
            },
            "gpioChip": ""
          },
          "io": {
            "controllerId": "27",
            "type": 1,
            "devicePath": "/run/devmap/xcvrs/xcvr_io_27"
            },
            "tcvrLaneToLedId": {"1": 27, "2": 27, "3": 27, "4": 27, "5": 27, "6": 27, "7": 27, "8": 27}        },
        "28": {
          "tcvrId": 28,
          "accessControl": {
            "controllerId": "28",
            "type": 1,
            "reset": {
              "sysfsPath": "/run/devmap/xcvrs/xcvr_ctrl_28/xcvr_reset_28",
              "mask": 1,
              "gpioOffset": 0,
              "resetHoldHi": 0
            },
            "presence": {
              "sysfsPath": "/run/devmap/xcvrs/xcvr_ctrl_28/xcvr_present_28",
              "mask": 1,
              "gpioOffset": 0,
              "presentHoldHi": 0
            },
            "gpioChip": ""
          },
          "io": {
            "controllerId": "28",
            "type": 1,
            "devicePath": "/run/devmap/xcvrs/xcvr_io_28"
            },
            "tcvrLaneToLedId": {"1": 28, "2": 28, "3": 28, "4": 28, "5": 28, "6": 28, "7": 28, "8": 28}        },
        "29": {
          "tcvrId": 29,
          "accessControl": {
            "controllerId": "29",
            "type": 1,
            "reset": {
              "sysfsPath": "/run/devmap/xcvrs/xcvr_ctrl_29/xcvr_reset_29",
              "mask": 1,
              "gpioOffset": 0,
              "resetHoldHi": 0
            },
            "presence": {
              "sysfsPath": "/run/devmap/xcvrs/xcvr_ctrl_29/xcvr_present_29",
              "mask": 1,
              "gpioOffset": 0,
              "presentHoldHi": 0
            },
            "gpioChip": ""
          },
          "io": {
            "controllerId": "29",
            "type": 1,
            "devicePath": "/run/devmap/xcvrs/xcvr_io_29"
            },
            "tcvrLaneToLedId": {"1": 29, "2": 29, "3": 29, "4": 29, "5": 29, "6": 29, "7": 29, "8": 29}        },
        "30": {
          "tcvrId": 30,
          "accessControl": {
            "controllerId": "30",
            "type": 1,
            "reset": {
              "sysfsPath": "/run/devmap/xcvrs/xcvr_ctrl_30/xcvr_reset_30",
              "mask": 1,
              "gpioOffset": 0,
              "resetHoldHi": 0
            },
            "presence": {
              "sysfsPath": "/run/devmap/xcvrs/xcvr_ctrl_30/xcvr_present_30",
              "mask": 1,
              "gpioOffset": 0,
              "presentHoldHi": 0
            },
            "gpioChip": ""
          },
          "io": {
            "controllerId": "30",
            "type": 1,
            "devicePath": "/run/devmap/xcvrs/xcvr_io_30"
            },
            "tcvrLaneToLedId": {"1": 30, "2": 30, "3": 30, "4": 30, "5": 30, "6": 30, "7": 30, "8": 30}        },
        "31": {
          "tcvrId": 31,
          "accessControl": {
            "controllerId": "31",
            "type": 1,
            "reset": {
              "sysfsPath": "/run/devmap/xcvrs/xcvr_ctrl_31/xcvr_reset_31",
              "mask": 1,
              "gpioOffset": 0,
              "resetHoldHi": 0
            },
            "presence": {
              "sysfsPath": "/run/devmap/xcvrs/xcvr_ctrl_31/xcvr_present_31",
              "mask": 1,
              "gpioOffset": 0,
              "presentHoldHi": 0
            },
            "gpioChip": ""
          },
          "io": {
            "controllerId": "31",
            "type": 1,
            "devicePath": "/run/devmap/xcvrs/xcvr_io_31"
            },
            "tcvrLaneToLedId": {"1": 31, "2": 31, "3": 31, "4": 31, "5": 31, "6": 31, "7": 31, "8": 31}        },
        "32": {
          "tcvrId": 32,
          "accessControl": {
            "controllerId": "32",
            "type": 1,
            "reset": {
              "sysfsPath": "/run/devmap/xcvrs/xcvr_ctrl_32/xcvr_reset_32",
              "mask": 1,
              "gpioOffset": 0,
              "resetHoldHi": 0
            },
            "presence": {
              "sysfsPath": "/run/devmap/xcvrs/xcvr_ctrl_32/xcvr_present_32",
              "mask": 1,
              "gpioOffset": 0,
              "presentHoldHi": 0
            },
            "gpioChip": ""
          },
          "io": {
            "controllerId": "32",
            "type": 1,
            "devicePath": "/run/devmap/xcvrs/xcvr_io_32"
            },
            "tcvrLaneToLedId": {"1": 32, "2": 32, "3": 32, "4": 32, "5": 32, "6": 32, "7": 32, "8": 32}        },
        "33": {
          "tcvrId": 33,
          "accessControl": {
            "controllerId": "33",
            "type": 1,
            "reset": {
              "sysfsPath": "/run/devmap/xcvrs/xcvr_ctrl_33/xcvr_reset_33",
              "mask": 1,
              "gpioOffset": 0,
              "resetHoldHi": 0
            },
            "presence": {
              "sysfsPath": "/run/devmap/xcvrs/xcvr_ctrl_33/xcvr_present_33",
              "mask": 1,
              "gpioOffset": 0,
              "presentHoldHi": 0
            },
            "gpioChip": ""
          },
          "io": {
            "controllerId": "33",
            "type": 1,
            "devicePath": "/run/devmap/xcvrs/xcvr_io_33"
            },
            "tcvrLaneToLedId": {"1": 33, "2": 33, "3": 33, "4": 33, "5": 33, "6": 33, "7": 33, "8": 33}        },
        "34": {
          "tcvrId": 34,
          "accessControl": {
            "controllerId": "34",
            "type": 1,
            "reset": {
              "sysfsPath": "/run/devmap/xcvrs/xcvr_ctrl_34/xcvr_reset_34",
              "mask": 1,
              "gpioOffset": 0,
              "resetHoldHi": 0
            },
            "presence": {
              "sysfsPath": "/run/devmap/xcvrs/xcvr_ctrl_34/xcvr_present_34",
              "mask": 1,
              "gpioOffset": 0,
              "presentHoldHi": 0
            },
            "gpioChip": ""
          },
          "io": {
            "controllerId": "34",
            "type": 1,
            "devicePath": "/run/devmap/xcvrs/xcvr_io_34"
            },
            "tcvrLaneToLedId": {"1": 34, "2": 34, "3": 34, "4": 34, "5": 34, "6": 34, "7": 34, "8": 34}        },
        "35": {
          "tcvrId": 35,
          "accessControl": {
            "controllerId": "35",
            "type": 1,
            "reset": {
              "sysfsPath": "/run/devmap/xcvrs/xcvr_ctrl_35/xcvr_reset_35",
              "mask": 1,
              "gpioOffset": 0,
              "resetHoldHi": 0
            },
            "presence": {
              "sysfsPath": "/run/devmap/xcvrs/xcvr_ctrl_35/xcvr_present_35",
              "mask": 1,
              "gpioOffset": 0,
              "presentHoldHi": 0
            },
            "gpioChip": ""
          },
          "io": {
            "controllerId": "35",
            "type": 1,
            "devicePath": "/run/devmap/xcvrs/xcvr_io_35"
            },
            "tcvrLaneToLedId": {"1": 35, "2": 35, "3": 35, "4": 35, "5": 35, "6": 35, "7": 35, "8": 35}        },
        "36": {
          "tcvrId": 36,
          "accessControl": {
            "controllerId": "36",
            "type": 1,
            "reset": {
              "sysfsPath": "/run/devmap/xcvrs/xcvr_ctrl_36/xcvr_reset_36",
              "mask": 1,
              "gpioOffset": 0,
              "resetHoldHi": 0
            },
            "presence": {
              "sysfsPath": "/run/devmap/xcvrs/xcvr_ctrl_36/xcvr_present_36",
              "mask": 1,
              "gpioOffset": 0,
              "presentHoldHi": 0
            },
            "gpioChip": ""
          },
          "io": {
            "controllerId": "36",
            "type": 1,
            "devicePath": "/run/devmap/xcvrs/xcvr_io_36"
            },
            "tcvrLaneToLedId": {"1": 36, "2": 36, "3": 36, "4": 36, "5": 36, "6": 36, "7": 36, "8": 36}        },
        "37": {
          "tcvrId": 37,
          "accessControl": {
            "controllerId": "37",
            "type": 1,
            "reset": {
              "sysfsPath": "/run/devmap/xcvrs/xcvr_ctrl_37/xcvr_reset_37",
              "mask": 1,
              "gpioOffset": 0,
              "resetHoldHi": 0
            },
            "presence": {
              "sysfsPath": "/run/devmap/xcvrs/xcvr_ctrl_37/xcvr_present_37",
              "mask": 1,
              "gpioOffset": 0,
              "presentHoldHi": 0
            },
            "gpioChip": ""
          },
          "io": {
            "controllerId": "37",
            "type": 1,
            "devicePath": "/run/devmap/xcvrs/xcvr_io_37"
            },
            "tcvrLaneToLedId": {"1": 37, "2": 37, "3": 37, "4": 37, "5": 37, "6": 37, "7": 37, "8": 37}        },
        "38": {
          "tcvrId": 38,
          "accessControl": {
            "controllerId": "38",
            "type": 1,
            "reset": {
              "sysfsPath": "/run/devmap/xcvrs/xcvr_ctrl_38/xcvr_reset_38",
              "mask": 1,
              "gpioOffset": 0,
              "resetHoldHi": 0
            },
            "presence": {
              "sysfsPath": "/run/devmap/xcvrs/xcvr_ctrl_38/xcvr_present_38",
              "mask": 1,
              "gpioOffset": 0,
              "presentHoldHi": 0
            },
            "gpioChip": ""
          },
          "io": {
            "controllerId": "38",
            "type": 1,
            "devicePath": "/run/devmap/xcvrs/xcvr_io_38"
            },
            "tcvrLaneToLedId": {"1": 38, "2": 38, "3": 38, "4": 38, "5": 38, "6": 38, "7": 38, "8": 38}        },
        "39": {
          "tcvrId": 39,
          "accessControl": {
            "controllerId": "39",
            "type": 1,
            "reset": {
              "sysfsPath": "/run/devmap/xcvrs/xcvr_ctrl_39/xcvr_reset_39",
              "mask": 1,
              "gpioOffset": 0,
              "resetHoldHi": 0
            },
            "presence": {
              "sysfsPath": "/run/devmap/xcvrs/xcvr_ctrl_39/xcvr_present_39",
              "mask": 1,
              "gpioOffset": 0,
              "presentHoldHi": 0
            },
            "gpioChip": ""
          },
          "io": {
            "controllerId": "39",
            "type": 1,
            "devicePath": "/run/devmap/xcvrs/xcvr_io_39"
            },
            "tcvrLaneToLedId": {"1": 39, "2": 39, "3": 39, "4": 39, "5": 39, "6": 39, "7": 39, "8": 39}        },
        "40": {
          "tcvrId": 40,
          "accessControl": {
            "controllerId": "40",
            "type": 1,
            "reset": {
              "sysfsPath": "/run/devmap/xcvrs/xcvr_ctrl_40/xcvr_reset_40",
              "mask": 1,
              "gpioOffset": 0,
              "resetHoldHi": 0
            },
            "presence": {
              "sysfsPath": "/run/devmap/xcvrs/xcvr_ctrl_40/xcvr_present_40",
              "mask": 1,
              "gpioOffset": 0,
              "presentHoldHi": 0
            },
            "gpioChip": ""
          },
          "io": {
            "controllerId": "40",
            "type": 1,
            "devicePath": "/run/devmap/xcvrs/xcvr_io_40"
            },
            "tcvrLaneToLedId": {"1": 40, "2": 40, "3": 40, "4": 40, "5": 40, "6": 40, "7": 40, "8": 40}        },
        "41": {
          "tcvrId": 41,
          "accessControl": {
            "controllerId": "41",
            "type": 1,
            "reset": {
              "sysfsPath": "/run/devmap/xcvrs/xcvr_ctrl_41/xcvr_reset_41",
              "mask": 1,
              "gpioOffset": 0,
              "resetHoldHi": 0
            },
            "presence": {
              "sysfsPath": "/run/devmap/xcvrs/xcvr_ctrl_41/xcvr_present_41",
              "mask": 1,
              "gpioOffset": 0,
              "presentHoldHi": 0
            },
            "gpioChip": ""
          },
          "io": {
            "controllerId": "41",
            "type": 1,
            "devicePath": "/run/devmap/xcvrs/xcvr_io_41"
            },
            "tcvrLaneToLedId": {"1": 41, "2": 41, "3": 41, "4": 41, "5": 41, "6": 41, "7": 41, "8": 41}        },
        "42": {
          "tcvrId": 42,
          "accessControl": {
            "controllerId": "42",
            "type": 1,
            "reset": {
              "sysfsPath": "/run/devmap/xcvrs/xcvr_ctrl_42/xcvr_reset_42",
              "mask": 1,
              "gpioOffset": 0,
              "resetHoldHi": 0
            },
            "presence": {
              "sysfsPath": "/run/devmap/xcvrs/xcvr_ctrl_42/xcvr_present_42",
              "mask": 1,
              "gpioOffset": 0,
              "presentHoldHi": 0
            },
            "gpioChip": ""
          },
          "io": {
            "controllerId": "42",
            "type": 1,
            "devicePath": "/run/devmap/xcvrs/xcvr_io_42"
            },
            "tcvrLaneToLedId": {"1": 42, "2": 42, "3": 42, "4": 42, "5": 42, "6": 42, "7": 42, "8": 42}        },
        "43": {
          "tcvrId": 43,
          "accessControl": {
            "controllerId": "43",
            "type": 1,
            "reset": {
              "sysfsPath": "/run/devmap/xcvrs/xcvr_ctrl_43/xcvr_reset_43",
              "mask": 1,
              "gpioOffset": 0,
              "resetHoldHi": 0
            },
            "presence": {
              "sysfsPath": "/run/devmap/xcvrs/xcvr_ctrl_43/xcvr_present_43",
              "mask": 1,
              "gpioOffset": 0,
              "presentHoldHi": 0
            },
            "gpioChip": ""
          },
          "io": {
            "controllerId": "43",
            "type": 1,
            "devicePath": "/run/devmap/xcvrs/xcvr_io_43"
            },
            "tcvrLaneToLedId": {"1": 43, "2": 43, "3": 43, "4": 43, "5": 43, "6": 43, "7": 43, "8": 43}        },
        "44": {
          "tcvrId": 44,
          "accessControl": {
            "controllerId": "44",
            "type": 1,
            "reset": {
              "sysfsPath": "/run/devmap/xcvrs/xcvr_ctrl_44/xcvr_reset_44",
              "mask": 1,
              "gpioOffset": 0,
              "resetHoldHi": 0
            },
            "presence": {
              "sysfsPath": "/run/devmap/xcvrs/xcvr_ctrl_44/xcvr_present_44",
              "mask": 1,
              "gpioOffset": 0,
              "presentHoldHi": 0
            },
            "gpioChip": ""
          },
          "io": {
            "controllerId": "44",
            "type": 1,
            "devicePath": "/run/devmap/xcvrs/xcvr_io_44"
            },
            "tcvrLaneToLedId": {"1": 44, "2": 44, "3": 44, "4": 44, "5": 44, "6": 44, "7": 44, "8": 44}        },
        "45": {
          "tcvrId": 45,
          "accessControl": {
            "controllerId": "45",
            "type": 1,
            "reset": {
              "sysfsPath": "/run/devmap/xcvrs/xcvr_ctrl_45/xcvr_reset_45",
              "mask": 1,
              "gpioOffset": 0,
              "resetHoldHi": 0
            },
            "presence": {
              "sysfsPath": "/run/devmap/xcvrs/xcvr_ctrl_45/xcvr_present_45",
              "mask": 1,
              "gpioOffset": 0,
              "presentHoldHi": 0
            },
            "gpioChip": ""
          },
          "io": {
            "controllerId": "45",
            "type": 1,
            "devicePath": "/run/devmap/xcvrs/xcvr_io_45"
            },
            "tcvrLaneToLedId": {"1": 45, "2": 45, "3": 45, "4": 45, "5": 45, "6": 45, "7": 45, "8": 45}        },
        "46": {
          "tcvrId": 46,
          "accessControl": {
            "controllerId": "46",
            "type": 1,
            "reset": {
              "sysfsPath": "/run/devmap/xcvrs/xcvr_ctrl_46/xcvr_reset_46",
              "mask": 1,
              "gpioOffset": 0,
              "resetHoldHi": 0
            },
            "presence": {
              "sysfsPath": "/run/devmap/xcvrs/xcvr_ctrl_46/xcvr_present_46",
              "mask": 1,
              "gpioOffset": 0,
              "presentHoldHi": 0
            },
            "gpioChip": ""
          },
          "io": {
            "controllerId": "46",
            "type": 1,
            "devicePath": "/run/devmap/xcvrs/xcvr_io_46"
            },
            "tcvrLaneToLedId": {"1": 46, "2": 46, "3": 46, "4": 46, "5": 46, "6": 46, "7": 46, "8": 46}        },
        "47": {
          "tcvrId": 47,
          "accessControl": {
            "controllerId": "47",
            "type": 1,
            "reset": {
              "sysfsPath": "/run/devmap/xcvrs/xcvr_ctrl_47/xcvr_reset_47",
              "mask": 1,
              "gpioOffset": 0,
              "resetHoldHi": 0
            },
            "presence": {
              "sysfsPath": "/run/devmap/xcvrs/xcvr_ctrl_47/xcvr_present_47",
              "mask": 1,
              "gpioOffset": 0,
              "presentHoldHi": 0
            },
            "gpioChip": ""
          },
          "io": {
            "controllerId": "47",
            "type": 1,
            "devicePath": "/run/devmap/xcvrs/xcvr_io_47"
            },
            "tcvrLaneToLedId": {"1": 47, "2": 47, "3": 47, "4": 47, "5": 47, "6": 47, "7": 47, "8": 47}        },
        "48": {
          "tcvrId": 48,
          "accessControl": {
            "controllerId": "48",
            "type": 1,
            "reset": {
              "sysfsPath": "/run/devmap/xcvrs/xcvr_ctrl_48/xcvr_reset_48",
              "mask": 1,
              "gpioOffset": 0,
              "resetHoldHi": 0
            },
            "presence": {
              "sysfsPath": "/run/devmap/xcvrs/xcvr_ctrl_48/xcvr_present_48",
              "mask": 1,
              "gpioOffset": 0,
              "presentHoldHi": 0
            },
            "gpioChip": ""
          },
          "io": {
            "controllerId": "48",
            "type": 1,
            "devicePath": "/run/devmap/xcvrs/xcvr_io_48"
            },
            "tcvrLaneToLedId": {"1": 48, "2": 48, "3": 48, "4": 48, "5": 48, "6": 48, "7": 48, "8": 48}        },
        "49": {
          "tcvrId": 49,
          "accessControl": {
            "controllerId": "49",
            "type": 1,
            "reset": {
              "sysfsPath": "/run/devmap/xcvrs/xcvr_ctrl_49/xcvr_reset_49",
              "mask": 1,
              "gpioOffset": 0,
              "resetHoldHi": 0
            },
            "presence": {
              "sysfsPath": "/run/devmap/xcvrs/xcvr_ctrl_49/xcvr_present_49",
              "mask": 1,
              "gpioOffset": 0,
              "presentHoldHi": 0
            },
            "gpioChip": ""
          },
          "io": {
            "controllerId": "49",
            "type": 1,
            "devicePath": "/run/devmap/xcvrs/xcvr_io_49"
            },
            "tcvrLaneToLedId": {"1": 49, "2": 49, "3": 49, "4": 49, "5": 49, "6": 49, "7": 49, "8": 49}        },
        "50": {
          "tcvrId": 50,
          "accessControl": {
            "controllerId": "50",
            "type": 1,
            "reset": {
              "sysfsPath": "/run/devmap/xcvrs/xcvr_ctrl_50/xcvr_reset_50",
              "mask": 1,
              "gpioOffset": 0,
              "resetHoldHi": 0
            },
            "presence": {
              "sysfsPath": "/run/devmap/xcvrs/xcvr_ctrl_50/xcvr_present_50",
              "mask": 1,
              "gpioOffset": 0,
              "presentHoldHi": 0
            },
            "gpioChip": ""
          },
          "io": {
            "controllerId": "50",
            "type": 1,
            "devicePath": "/run/devmap/xcvrs/xcvr_io_50"
            },
            "tcvrLaneToLedId": {"1": 50, "2": 50, "3": 50, "4": 50, "5": 50, "6": 50, "7": 50, "8": 50}        },
        "51": {
          "tcvrId": 51,
          "accessControl": {
            "controllerId": "51",
            "type": 1,
            "reset": {
              "sysfsPath": "/run/devmap/xcvrs/xcvr_ctrl_51/xcvr_reset_51",
              "mask": 1,
              "gpioOffset": 0,
              "resetHoldHi": 0
            },
            "presence": {
              "sysfsPath": "/run/devmap/xcvrs/xcvr_ctrl_51/xcvr_present_51",
              "mask": 1,
              "gpioOffset": 0,
              "presentHoldHi": 0
            },
            "gpioChip": ""
          },
          "io": {
            "controllerId": "51",
            "type": 1,
            "devicePath": "/run/devmap/xcvrs/xcvr_io_51"
            },
            "tcvrLaneToLedId": {"1": 51, "2": 51, "3": 51, "4": 51, "5": 51, "6": 51, "7": 51, "8": 51}        },
        "52": {
          "tcvrId": 52,
          "accessControl": {
            "controllerId": "52",
            "type": 1,
            "reset": {
              "sysfsPath": "/run/devmap/xcvrs/xcvr_ctrl_52/xcvr_reset_52",
              "mask": 1,
              "gpioOffset": 0,
              "resetHoldHi": 0
            },
            "presence": {
              "sysfsPath": "/run/devmap/xcvrs/xcvr_ctrl_52/xcvr_present_52",
              "mask": 1,
              "gpioOffset": 0,
              "presentHoldHi": 0
            },
            "gpioChip": ""
          },
          "io": {
            "controllerId": "52",
            "type": 1,
            "devicePath": "/run/devmap/xcvrs/xcvr_io_52"
            },
            "tcvrLaneToLedId": {"1": 52, "2": 52, "3": 52, "4": 52, "5": 52, "6": 52, "7": 52, "8": 52}        },
        "53": {
          "tcvrId": 53,
          "accessControl": {
            "controllerId": "53",
            "type": 1,
            "reset": {
              "sysfsPath": "/run/devmap/xcvrs/xcvr_ctrl_53/xcvr_reset_53",
              "mask": 1,
              "gpioOffset": 0,
              "resetHoldHi": 0
            },
            "presence": {
              "sysfsPath": "/run/devmap/xcvrs/xcvr_ctrl_53/xcvr_present_53",
              "mask": 1,
              "gpioOffset": 0,
              "presentHoldHi": 0
            },
            "gpioChip": ""
          },
          "io": {
            "controllerId": "53",
            "type": 1,
            "devicePath": "/run/devmap/xcvrs/xcvr_io_53"
            },
            "tcvrLaneToLedId": {"1": 53, "2": 53, "3": 53, "4": 53, "5": 53, "6": 53, "7": 53, "8": 53}        },
        "54": {
          "tcvrId": 54,
          "accessControl": {
            "controllerId": "54",
            "type": 1,
            "reset": {
              "sysfsPath": "/run/devmap/xcvrs/xcvr_ctrl_54/xcvr_reset_54",
              "mask": 1,
              "gpioOffset": 0,
              "resetHoldHi": 0
            },
            "presence": {
              "sysfsPath": "/run/devmap/xcvrs/xcvr_ctrl_54/xcvr_present_54",
              "mask": 1,
              "gpioOffset": 0,
              "presentHoldHi": 0
            },
            "gpioChip": ""
          },
          "io": {
            "controllerId": "54",
            "type": 1,
            "devicePath": "/run/devmap/xcvrs/xcvr_io_54"
            },
            "tcvrLaneToLedId": {"1": 54, "2": 54, "3": 54, "4": 54, "5": 54, "6": 54, "7": 54, "8": 54}        },
        "55": {
          "tcvrId": 55,
          "accessControl": {
            "controllerId": "55",
            "type": 1,
            "reset": {
              "sysfsPath": "/run/devmap/xcvrs/xcvr_ctrl_55/xcvr_reset_55",
              "mask": 1,
              "gpioOffset": 0,
              "resetHoldHi": 0
            },
            "presence": {
              "sysfsPath": "/run/devmap/xcvrs/xcvr_ctrl_55/xcvr_present_55",
              "mask": 1,
              "gpioOffset": 0,
              "presentHoldHi": 0
            },
            "gpioChip": ""
          },
          "io": {
            "controllerId": "55",
            "type": 1,
            "devicePath": "/run/devmap/xcvrs/xcvr_io_55"
            },
            "tcvrLaneToLedId": {"1": 55, "2": 55, "3": 55, "4": 55, "5": 55, "6": 55, "7": 55, "8": 55}        },
        "56": {
          "tcvrId": 56,
          "accessControl": {
            "controllerId": "56",
            "type": 1,
            "reset": {
              "sysfsPath": "/run/devmap/xcvrs/xcvr_ctrl_56/xcvr_reset_56",
              "mask": 1,
              "gpioOffset": 0,
              "resetHoldHi": 0
            },
            "presence": {
              "sysfsPath": "/run/devmap/xcvrs/xcvr_ctrl_56/xcvr_present_56",
              "mask": 1,
              "gpioOffset": 0,
              "presentHoldHi": 0
            },
            "gpioChip": ""
          },
          "io": {
            "controllerId": "56",
            "type": 1,
            "devicePath": "/run/devmap/xcvrs/xcvr_io_56"
            },
            "tcvrLaneToLedId": {"1": 56, "2": 56, "3": 56, "4": 56, "5": 56, "6": 56, "7": 56, "8": 56}        },
        "57": {
          "tcvrId": 57,
          "accessControl": {
            "controllerId": "57",
            "type": 1,
            "reset": {
              "sysfsPath": "/run/devmap/xcvrs/xcvr_ctrl_57/xcvr_reset_57",
              "mask": 1,
              "gpioOffset": 0,
              "resetHoldHi": 0
            },
            "presence": {
              "sysfsPath": "/run/devmap/xcvrs/xcvr_ctrl_57/xcvr_present_57",
              "mask": 1,
              "gpioOffset": 0,
              "presentHoldHi": 0
            },
            "gpioChip": ""
          },
          "io": {
            "controllerId": "57",
            "type": 1,
            "devicePath": "/run/devmap/xcvrs/xcvr_io_57"
            },
            "tcvrLaneToLedId": {"1": 57, "2": 57, "3": 57, "4": 57, "5": 57, "6": 57, "7": 57, "8": 57}        },
        "58": {
          "tcvrId": 58,
          "accessControl": {
            "controllerId": "58",
            "type": 1,
            "reset": {
              "sysfsPath": "/run/devmap/xcvrs/xcvr_ctrl_58/xcvr_reset_58",
              "mask": 1,
              "gpioOffset": 0,
              "resetHoldHi": 0
            },
            "presence": {
              "sysfsPath": "/run/devmap/xcvrs/xcvr_ctrl_58/xcvr_present_58",
              "mask": 1,
              "gpioOffset": 0,
              "presentHoldHi": 0
            },
            "gpioChip": ""
          },
          "io": {
            "controllerId": "58",
            "type": 1,
            "devicePath": "/run/devmap/xcvrs/xcvr_io_58"
            },
            "tcvrLaneToLedId": {"1": 58, "2": 58, "3": 58, "4": 58, "5": 58, "6": 58, "7": 58, "8": 58}        },
        "59": {
          "tcvrId": 59,
          "accessControl": {
            "controllerId": "59",
            "type": 1,
            "reset": {
              "sysfsPath": "/run/devmap/xcvrs/xcvr_ctrl_59/xcvr_reset_59",
              "mask": 1,
              "gpioOffset": 0,
              "resetHoldHi": 0
            },
            "presence": {
              "sysfsPath": "/run/devmap/xcvrs/xcvr_ctrl_59/xcvr_present_59",
              "mask": 1,
              "gpioOffset": 0,
              "presentHoldHi": 0
            },
            "gpioChip": ""
          },
          "io": {
            "controllerId": "59",
            "type": 1,
            "devicePath": "/run/devmap/xcvrs/xcvr_io_59"
            },
            "tcvrLaneToLedId": {"1": 59, "2": 59, "3": 59, "4": 59, "5": 59, "6": 59, "7": 59, "8": 59}        },
        "60": {
          "tcvrId": 60,
          "accessControl": {
            "controllerId": "60",
            "type": 1,
            "reset": {
              "sysfsPath": "/run/devmap/xcvrs/xcvr_ctrl_60/xcvr_reset_60",
              "mask": 1,
              "gpioOffset": 0,
              "resetHoldHi": 0
            },
            "presence": {
              "sysfsPath": "/run/devmap/xcvrs/xcvr_ctrl_60/xcvr_present_60",
              "mask": 1,
              "gpioOffset": 0,
              "presentHoldHi": 0
            },
            "gpioChip": ""
          },
          "io": {
            "controllerId": "60",
            "type": 1,
            "devicePath": "/run/devmap/xcvrs/xcvr_io_60"
            },
            "tcvrLaneToLedId": {"1": 60, "2": 60, "3": 60, "4": 60, "5": 60, "6": 60, "7": 60, "8": 60}        },
        "61": {
          "tcvrId": 61,
          "accessControl": {
            "controllerId": "61",
            "type": 1,
            "reset": {
              "sysfsPath": "/run/devmap/xcvrs/xcvr_ctrl_61/xcvr_reset_61",
              "mask": 1,
              "gpioOffset": 0,
              "resetHoldHi": 0
            },
            "presence": {
              "sysfsPath": "/run/devmap/xcvrs/xcvr_ctrl_61/xcvr_present_61",
              "mask": 1,
              "gpioOffset": 0,
              "presentHoldHi": 0
            },
            "gpioChip": ""
          },
          "io": {
            "controllerId": "61",
            "type": 1,
            "devicePath": "/run/devmap/xcvrs/xcvr_io_61"
            },
            "tcvrLaneToLedId": {"1": 61, "2": 61, "3": 61, "4": 61, "5": 61, "6": 61, "7": 61, "8": 61}        },
        "62": {
          "tcvrId": 62,
          "accessControl": {
            "controllerId": "62",
            "type": 1,
            "reset": {
              "sysfsPath": "/run/devmap/xcvrs/xcvr_ctrl_62/xcvr_reset_62",
              "mask": 1,
              "gpioOffset": 0,
              "resetHoldHi": 0
            },
            "presence": {
              "sysfsPath": "/run/devmap/xcvrs/xcvr_ctrl_62/xcvr_present_62",
              "mask": 1,
              "gpioOffset": 0,
              "presentHoldHi": 0
            },
            "gpioChip": ""
          },
          "io": {
            "controllerId": "62",
            "type": 1,
            "devicePath": "/run/devmap/xcvrs/xcvr_io_62"
            },
            "tcvrLaneToLedId": {"1": 62, "2": 62, "3": 62, "4": 62, "5": 62, "6": 62, "7": 62, "8": 62}        },
        "63": {
          "tcvrId": 63,
          "accessControl": {
            "controllerId": "63",
            "type": 1,
            "reset": {
              "sysfsPath": "/run/devmap/xcvrs/xcvr_ctrl_63/xcvr_reset_63",
              "mask": 1,
              "gpioOffset": 0,
              "resetHoldHi": 0
            },
            "presence": {
              "sysfsPath": "/run/devmap/xcvrs/xcvr_ctrl_63/xcvr_present_63",
              "mask": 1,
              "gpioOffset": 0,
              "presentHoldHi": 0
            },
            "gpioChip": ""
          },
          "io": {
            "controllerId": "63",
            "type": 1,
            "devicePath": "/run/devmap/xcvrs/xcvr_io_63"
            },
            "tcvrLaneToLedId": {"1": 63, "2": 63, "3": 63, "4": 63, "5": 63, "6": 63, "7": 63, "8": 63}        },
        "64": {
          "tcvrId": 64,
          "accessControl": {
            "controllerId": "64",
            "type": 1,
            "reset": {
              "sysfsPath": "/run/devmap/xcvrs/xcvr_ctrl_64/xcvr_reset_64",
              "mask": 1,
              "gpioOffset": 0,
              "resetHoldHi": 0
            },
            "presence": {
              "sysfsPath": "/run/devmap/xcvrs/xcvr_ctrl_64/xcvr_present_64",
              "mask": 1,
              "gpioOffset": 0,
              "presentHoldHi": 0
            },
            "gpioChip": ""
          },
          "io": {
            "controllerId": "64",
            "type": 1,
            "devicePath": "/run/devmap/xcvrs/xcvr_io_64"
            },
            "tcvrLaneToLedId": {"1": 64, "2": 64, "3": 64, "4": 64, "5": 64, "6": 64, "7": 64, "8": 64}        }
      },
      "phyMapping": {},
      "phyIOControllers": {},
      "ledMapping": {
        "1": {
          "id": 1,
          "bluePath": "/sys/class/leds/port1_led1:blue:status",
          "yellowPath": "/sys/class/leds/port1_led2:amber:status",
          "transceiverId": 1
        },
        "2": {
          "id": 2,
          "bluePath": "/sys/class/leds/port2_led1:blue:status",
          "yellowPath": "/sys/class/leds/port2_led2:amber:status",
          "transceiverId": 2
        },
        "3": {
          "id": 3,
          "bluePath": "/sys/class/leds/port3_led1:blue:status",
          "yellowPath": "/sys/class/leds/port3_led2:amber:status",
          "transceiverId": 3
        },
        "4": {
          "id": 4,
          "bluePath": "/sys/class/leds/port4_led1:blue:status",
          "yellowPath": "/sys/class/leds/port4_led2:amber:status",
          "transceiverId": 4
        },
        "5": {
          "id": 5,
          "bluePath": "/sys/class/leds/port5_led1:blue:status",
          "yellowPath": "/sys/class/leds/port5_led2:amber:status",
          "transceiverId": 5
        },
        "6": {
          "id": 6,
          "bluePath": "/sys/class/leds/port6_led1:blue:status",
          "yellowPath": "/sys/class/leds/port6_led2:amber:status",
          "transceiverId": 6
        },
        "7": {
          "id": 7,
          "bluePath": "/sys/class/leds/port7_led1:blue:status",
          "yellowPath": "/sys/class/leds/port7_led2:amber:status",
          "transceiverId": 7
        },
        "8": {
          "id": 8,
          "bluePath": "/sys/class/leds/port8_led1:blue:status",
          "yellowPath": "/sys/class/leds/port8_led2:amber:status",
          "transceiverId": 8
        },
        "9": {
          "id": 9,
          "bluePath": "/sys/class/leds/port9_led1:blue:status",
          "yellowPath": "/sys/class/leds/port9_led2:amber:status",
          "transceiverId": 9
        },
        "10": {
          "id": 10,
          "bluePath": "/sys/class/leds/port10_led1:blue:status",
          "yellowPath": "/sys/class/leds/port10_led2:amber:status",
          "transceiverId": 10
        },
        "11": {
          "id": 11,
          "bluePath": "/sys/class/leds/port11_led1:blue:status",
          "yellowPath": "/sys/class/leds/port11_led2:amber:status",
          "transceiverId": 11
        },
        "12": {
          "id": 12,
          "bluePath": "/sys/class/leds/port12_led1:blue:status",
          "yellowPath": "/sys/class/leds/port12_led2:amber:status",
          "transceiverId": 12
        },
        "13": {
          "id": 13,
          "bluePath": "/sys/class/leds/port13_led1:blue:status",
          "yellowPath": "/sys/class/leds/port13_led2:amber:status",
          "transceiverId": 13
        },
        "14": {
          "id": 14,
          "bluePath": "/sys/class/leds/port14_led1:blue:status",
          "yellowPath": "/sys/class/leds/port14_led2:amber:status",
          "transceiverId": 14
        },
        "15": {
          "id": 15,
          "bluePath": "/sys/class/leds/port15_led1:blue:status",
          "yellowPath": "/sys/class/leds/port15_led2:amber:status",
          "transceiverId": 15
        },
        "16": {
          "id": 16,
          "bluePath": "/sys/class/leds/port16_led1:blue:status",
          "yellowPath": "/sys/class/leds/port16_led2:amber:status",
          "transceiverId": 16
        },
        "17": {
          "id": 17,
          "bluePath": "/sys/class/leds/port17_led1:blue:status",
          "yellowPath": "/sys/class/leds/port17_led2:amber:status",
          "transceiverId": 17
        },
        "18": {
          "id": 18,
          "bluePath": "/sys/class/leds/port18_led1:blue:status",
          "yellowPath": "/sys/class/leds/port18_led2:amber:status",
          "transceiverId": 18
        },
        "19": {
          "id": 19,
          "bluePath": "/sys/class/leds/port19_led1:blue:status",
          "yellowPath": "/sys/class/leds/port19_led2:amber:status",
          "transceiverId": 19
        },
        "20": {
          "id": 20,
          "bluePath": "/sys/class/leds/port20_led1:blue:status",
          "yellowPath": "/sys/class/leds/port20_led2:amber:status",
          "transceiverId": 20
        },
        "21": {
          "id": 21,
          "bluePath": "/sys/class/leds/port21_led1:blue:status",
          "yellowPath": "/sys/class/leds/port21_led2:amber:status",
          "transceiverId": 21
        },
        "22": {
          "id": 22,
          "bluePath": "/sys/class/leds/port22_led1:blue:status",
          "yellowPath": "/sys/class/leds/port22_led2:amber:status",
          "transceiverId": 22
        },
        "23": {
          "id": 23,
          "bluePath": "/sys/class/leds/port23_led1:blue:status",
          "yellowPath": "/sys/class/leds/port23_led2:amber:status",
          "transceiverId": 23
        },
        "24": {
          "id": 24,
          "bluePath": "/sys/class/leds/port24_led1:blue:status",
          "yellowPath": "/sys/class/leds/port24_led2:amber:status",
          "transceiverId": 24
        },
        "25": {
          "id": 25,
          "bluePath": "/sys/class/leds/port25_led1:blue:status",
          "yellowPath": "/sys/class/leds/port25_led2:amber:status",
          "transceiverId": 25
        },
        "26": {
          "id": 26,
          "bluePath": "/sys/class/leds/port26_led1:blue:status",
          "yellowPath": "/sys/class/leds/port26_led2:amber:status",
          "transceiverId": 26
        },
        "27": {
          "id": 27,
          "bluePath": "/sys/class/leds/port27_led1:blue:status",
          "yellowPath": "/sys/class/leds/port27_led2:amber:status",
          "transceiverId": 27
        },
        "28": {
          "id": 28,
          "bluePath": "/sys/class/leds/port28_led1:blue:status",
          "yellowPath": "/sys/class/leds/port28_led2:amber:status",
          "transceiverId": 28
        },
        "29": {
          "id": 29,
          "bluePath": "/sys/class/leds/port29_led1:blue:status",
          "yellowPath": "/sys/class/leds/port29_led2:amber:status",
          "transceiverId": 29
        },
        "30": {
          "id": 30,
          "bluePath": "/sys/class/leds/port30_led1:blue:status",
          "yellowPath": "/sys/class/leds/port30_led2:amber:status",
          "transceiverId": 30
        },
        "31": {
          "id": 31,
          "bluePath": "/sys/class/leds/port31_led1:blue:status",
          "yellowPath": "/sys/class/leds/port31_led2:amber:status",
          "transceiverId": 31
        },
        "32": {
          "id": 32,
          "bluePath": "/sys/class/leds/port32_led1:blue:status",
          "yellowPath": "/sys/class/leds/port32_led2:amber:status",
          "transceiverId": 32
        },
        "33": {
          "id": 33,
          "bluePath": "/sys/class/leds/port33_led1:blue:status",
          "yellowPath": "/sys/class/leds/port33_led2:amber:status",
          "transceiverId": 33
        },
        "34": {
          "id": 34,
          "bluePath": "/sys/class/leds/port34_led1:blue:status",
          "yellowPath": "/sys/class/leds/port34_led2:amber:status",
          "transceiverId": 34
        },
        "35": {
          "id": 35,
          "bluePath": "/sys/class/leds/port35_led1:blue:status",
          "yellowPath": "/sys/class/leds/port35_led2:amber:status",
          "transceiverId": 35
        },
        "36": {
          "id": 36,
          "bluePath": "/sys/class/leds/port36_led1:blue:status",
          "yellowPath": "/sys/class/leds/port36_led2:amber:status",
          "transceiverId": 36
        },
        "37": {
          "id": 37,
          "bluePath": "/sys/class/leds/port37_led1:blue:status",
          "yellowPath": "/sys/class/leds/port37_led2:amber:status",
          "transceiverId": 37
        },
        "38": {
          "id": 38,
          "bluePath": "/sys/class/leds/port38_led1:blue:status",
          "yellowPath": "/sys/class/leds/port38_led2:amber:status",
          "transceiverId": 38
        },
        "39": {
          "id": 39,
          "bluePath": "/sys/class/leds/port39_led1:blue:status",
          "yellowPath": "/sys/class/leds/port39_led2:amber:status",
          "transceiverId": 39
        },
        "40": {
          "id": 40,
          "bluePath": "/sys/class/leds/port40_led1:blue:status",
          "yellowPath": "/sys/class/leds/port40_led2:amber:status",
          "transceiverId": 40
        },
        "41": {
          "id": 41,
          "bluePath": "/sys/class/leds/port41_led1:blue:status",
          "yellowPath": "/sys/class/leds/port41_led2:amber:status",
          "transceiverId": 41
        },
        "42": {
          "id": 42,
          "bluePath": "/sys/class/leds/port42_led1:blue:status",
          "yellowPath": "/sys/class/leds/port42_led2:amber:status",
          "transceiverId": 42
        },
        "43": {
          "id": 43,
          "bluePath": "/sys/class/leds/port43_led1:blue:status",
          "yellowPath": "/sys/class/leds/port43_led2:amber:status",
          "transceiverId": 43
        },
        "44": {
          "id": 44,
          "bluePath": "/sys/class/leds/port44_led1:blue:status",
          "yellowPath": "/sys/class/leds/port44_led2:amber:status",
          "transceiverId": 44
        },
        "45": {
          "id": 45,
          "bluePath": "/sys/class/leds/port45_led1:blue:status",
          "yellowPath": "/sys/class/leds/port45_led2:amber:status",
          "transceiverId": 45
        },
        "46": {
          "id": 46,
          "bluePath": "/sys/class/leds/port46_led1:blue:status",
          "yellowPath": "/sys/class/leds/port46_led2:amber:status",
          "transceiverId": 46
        },
        "47": {
          "id": 47,
          "bluePath": "/sys/class/leds/port47_led1:blue:status",
          "yellowPath": "/sys/class/leds/port47_led2:amber:status",
          "transceiverId": 47
        },
        "48": {
          "id": 48,
          "bluePath": "/sys/class/leds/port48_led1:blue:status",
          "yellowPath": "/sys/class/leds/port48_led2:amber:status",
          "transceiverId": 48
        },
        "49": {
          "id": 49,
          "bluePath": "/sys/class/leds/port49_led1:blue:status",
          "yellowPath": "/sys/class/leds/port49_led2:amber:status",
          "transceiverId": 49
        },
        "50": {
          "id": 50,
          "bluePath": "/sys/class/leds/port50_led1:blue:status",
          "yellowPath": "/sys/class/leds/port50_led2:amber:status",
          "transceiverId": 50
        },
        "51": {
          "id": 51,
          "bluePath": "/sys/class/leds/port51_led1:blue:status",
          "yellowPath": "/sys/class/leds/port51_led2:amber:status",
          "transceiverId": 51
        },
        "52": {
          "id": 52,
          "bluePath": "/sys/class/leds/port52_led1:blue:status",
          "yellowPath": "/sys/class/leds/port52_led2:amber:status",
          "transceiverId": 52
        },
        "53": {
          "id": 53,
          "bluePath": "/sys/class/leds/port53_led1:blue:status",
          "yellowPath": "/sys/class/leds/port53_led2:amber:status",
          "transceiverId": 53
        },
        "54": {
          "id": 54,
          "bluePath": "/sys/class/leds/port54_led1:blue:status",
          "yellowPath": "/sys/class/leds/port54_led2:amber:status",
          "transceiverId": 54
        },
        "55": {
          "id": 55,
          "bluePath": "/sys/class/leds/port55_led1:blue:status",
          "yellowPath": "/sys/class/leds/port55_led2:amber:status",
          "transceiverId": 55
        },
        "56": {
          "id": 56,
          "bluePath": "/sys/class/leds/port56_led1:blue:status",
          "yellowPath": "/sys/class/leds/port56_led2:amber:status",
          "transceiverId": 56
        },
        "57": {
          "id": 57,
          "bluePath": "/sys/class/leds/port57_led1:blue:status",
          "yellowPath": "/sys/class/leds/port57_led2:amber:status",
          "transceiverId": 57
        },
        "58": {
          "id": 58,
          "bluePath": "/sys/class/leds/port58_led1:blue:status",
          "yellowPath": "/sys/class/leds/port58_led2:amber:status",
          "transceiverId": 58
        },
        "59": {
          "id": 59,
          "bluePath": "/sys/class/leds/port59_led1:blue:status",
          "yellowPath": "/sys/class/leds/port59_led2:amber:status",
          "transceiverId": 59
        },
        "60": {
          "id": 60,
          "bluePath": "/sys/class/leds/port60_led1:blue:status",
          "yellowPath": "/sys/class/leds/port60_led2:amber:status",
          "transceiverId": 60
        },
        "61": {
          "id": 61,
          "bluePath": "/sys/class/leds/port61_led1:blue:status",
          "yellowPath": "/sys/class/leds/port61_led2:amber:status",
          "transceiverId": 61
        },
        "62": {
          "id": 62,
          "bluePath": "/sys/class/leds/port62_led1:blue:status",
          "yellowPath": "/sys/class/leds/port62_led2:amber:status",
          "transceiverId": 62
        },
        "63": {
          "id": 63,
          "bluePath": "/sys/class/leds/port63_led1:blue:status",
          "yellowPath": "/sys/class/leds/port63_led2:amber:status",
          "transceiverId": 63
        },
        "64": {
          "id": 64,
          "bluePath": "/sys/class/leds/port64_led1:blue:status",
          "yellowPath": "/sys/class/leds/port64_led2:amber:status",
          "transceiverId": 64
        }
      }
    }
  }
}
)";

BspPlatformMappingThrift buildNh4220fPlatformMapping(
    const std::string& platformMappingStr) {
  return apache::thrift::SimpleJSONSerializer::deserialize<
      BspPlatformMappingThrift>(platformMappingStr);
}

} // namespace

namespace facebook::fboss {

Nh4220fBspPlatformMapping::Nh4220fBspPlatformMapping()
    : BspPlatformMapping(
          buildNh4220fPlatformMapping(kJsonBspPlatformMappingStr)) {}

Nh4220fBspPlatformMapping::Nh4220fBspPlatformMapping(
    const std::string& platformMappingStr)
    : BspPlatformMapping(buildNh4220fPlatformMapping(platformMappingStr)) {}

} // namespace facebook::fboss
