"""Hand-written SAI switch library targets for OSS Bazel build.

Source file lists derived from Meta's internal switch.bzl, with facebook/
files replaced by oss/ equivalents.  BCM uses npu/bcm/ overrides; fake uses
oss/ stubs only (mirrors cmake/AgentHwSaiSwitch.cmake else() branch).
"""

load("@rules_cc//cc:defs.bzl", "cc_library")

# -DSAI_VERSION_13_3_0_0_ODP must be absent for fake SAI; mirrors sai_api.
_SAI_COPTS = select({
    "//fboss/agent/hw/sai:is_bcm": ["-DSAI_VERSION_13_3_0_0_ODP"],
    "//fboss/agent/hw/sai:is_fake": [],
})

# Matches _COMMON_SRCS from Meta's switch.bzl
_COMMON_SRCS = [
    "ConcurrentIndices.cpp",
    "SaiAclTableGroupManager.cpp",
    "SaiAclTableManager.cpp",
    "SaiArsManager.cpp",
    "SaiArsProfileManager.cpp",
    "SaiBridgeManager.cpp",
    "SaiBufferManager.cpp",
    "SaiCounterManager.cpp",
    "SaiDebugCounterManager.cpp",
    "SaiInSegEntryManager.cpp",
    "SaiFdbManager.cpp",
    "SaiHashManager.cpp",
    "SaiHostifManager.cpp",
    "SaiLagManager.cpp",
    "SaiMacsecManager.cpp",
    "SaiManagerTable.cpp",
    "SaiMirrorManager.cpp",
    "SaiNeighborManager.cpp",
    "SaiNextHopManager.cpp",
    "SaiNextHopGroupManager.cpp",
    "SaiPortManager.cpp",
    "SaiPortUtils.cpp",
    "SaiQosMapManager.cpp",
    "SaiQueueManager.cpp",
    "SaiRouteManager.cpp",
    "SaiRouterInterfaceManager.cpp",
    "SaiRxPacket.cpp",
    "SaiSamplePacketManager.cpp",
    "SaiSchedulerManager.cpp",
    "SaiSwitch.cpp",
    "SaiSwitchManager.cpp",
    "SaiSystemPortManager.cpp",
    "SaiUdfManager.cpp",
    "SaiVlanManager.cpp",
    "SaiVirtualRouterManager.cpp",
    "SaiWredManager.cpp",
    "SaiTunnelManager.cpp",
    "SaiSrv6MySidManager.cpp",
    "SaiSrv6SidListManager.cpp",
    "SaiSrv6TunnelManager.cpp",
    "SaiTunnelUtils.cpp",
]

# Matches _NPU_BRCM_SRCS from Meta's switch.bzl, with:
# - facebook/SaiSwitchManager.cpp → oss/SaiSwitchManager.cpp
# - npu/bcm/facebook/SaiVendorSwitchManager.cpp dropped (oss/ used instead)
_NPU_BRCM_OSS_SRCS = _COMMON_SRCS + [
    "npu/SaiAclTableManager.cpp",
    "npu/SaiPortManager.cpp",
    "npu/SaiSwitch.cpp",
    # BCM-specific overrides
    "npu/bcm/SaiArsManager.cpp",
    "npu/bcm/SaiBufferManager.cpp",
    "npu/bcm/SaiFirmwareManager.cpp",
    "npu/bcm/SaiPortManager.cpp",
    "npu/bcm/SaiQueueManager.cpp",
    "npu/bcm/SaiSwitch.cpp",
    "npu/bcm/SaiSwitchManager.cpp",
    "npu/bcm/SaiTamManager.cpp",
    # OSS stubs (replace facebook/ and npu/bcm/facebook/ internal files)
    "npu/bcm/oss/SaiSwitchManager.cpp",
    "oss/SaiAclTableManager.cpp",
    "oss/SaiArsProfileManager.cpp",
    "oss/SaiVendorSwitchManager.cpp",
]

# Matches cmake/AgentHwSaiSwitch.cmake else() branch (fake / no vendor SDK).
# Uses npu/ common overrides + all oss/ stubs; no npu/bcm/ files.
_OSS_FAKE_SRCS = _COMMON_SRCS + [
    "npu/SaiAclTableManager.cpp",
    "npu/SaiPortManager.cpp",
    "npu/SaiSwitch.cpp",
    "oss/SaiAclTableManager.cpp",
    "oss/SaiArsManager.cpp",
    "oss/SaiArsProfileManager.cpp",
    "oss/SaiBufferManager.cpp",
    "oss/SaiFirmwareManager.cpp",
    "oss/SaiPortManager.cpp",
    "oss/SaiQueueManager.cpp",
    "oss/SaiSwitch.cpp",
    "oss/SaiSwitchManager.cpp",
    "oss/SaiTamManager.cpp",
    "oss/SaiVendorSwitchManager.cpp",
]

def sai_switch_impl():
    """Define SAI switch and thrift handler libraries."""

    cc_library(
        name = "sai_switch",
        srcs = select({
            "//fboss/agent/hw/sai:is_bcm": _NPU_BRCM_OSS_SRCS,
            "//fboss/agent/hw/sai:is_fake": _OSS_FAKE_SRCS,
        }),
        hdrs = native.glob(["*.h"]),
        copts = _SAI_COPTS,
        deps = [
            ":if",
            "//fboss/agent:core",
            "//fboss/agent:fboss-error",
            "//fboss/agent:fboss-types",
            "//fboss/agent:hw_switch",
            "//fboss/agent/hw:hardware_stats",
            "//fboss/agent/hw:hw_cpu_fb303_stats",
            "//fboss/agent/hw:hw_fb303_stats",
            "//fboss/agent/hw:hw_port_fb303_stats",
            "//fboss/agent/hw:hw_resource_stats_publisher",
            "//fboss/agent/hw:hw_rif_fb303_stats",
            "//fboss/agent/hw:hw_switch_warmboot_helper",
            "//fboss/agent/hw:hw_trunk_counters",
            "//fboss/agent/hw/sai/api:sai_api",
            "//fboss/agent/hw/sai/store:sai_store",
            "//fboss/agent/state:state",
            "//fboss/lib:ref_map",
            "//fboss/lib/phy:phy_utils",
            "//fboss/mka_service/if:mka_structs",
            "@fb303//:fb303",
            "@folly//:folly",
            "@glog//:glog",
            "@googletest//:googletest",
        ] + select({
            "//fboss/agent/hw/sai:is_bcm": ["@sai_impl//:sai_impl"],
            "//fboss/agent/hw/sai:is_fake": ["//fboss/agent/hw/sai/fake:fake_sai"],
        }),
        visibility = ["//visibility:public"],
    )

    cc_library(
        name = "thrift_handler",
        srcs = ["SaiHandler.cpp"],
        hdrs = ["SaiHandler.h"],
        copts = _SAI_COPTS,
        deps = [
            ":if",
            ":sai_switch",
            "//fboss/agent:handler",
            "//fboss/agent/hw/sai/diag:diag_lib",
            "@folly//:folly",
        ],
        visibility = ["//visibility:public"],
    )
