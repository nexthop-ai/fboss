"""Hand-written SAI API library targets for OSS Bazel build.

Source file lists derived from Meta's internal api.bzl.
BCM uses bcm/ variant sources; fake uses fake/FakeSaiExtensions.cpp.
"""

load("@rules_cc//cc:defs.bzl", "cc_library")

# -DSAI_VERSION_13_3_0_0_ODP expands to BRCM_SAI_SDK_* macros in SaiVersion.h;
# it must be absent for fake SAI.  All other SAI defines stay global in .bazelrc.
_SAI_COPTS = select({
    "//fboss/agent/hw/sai:is_bcm": ["-DSAI_VERSION_13_3_0_0_ODP"],
    "//fboss/agent/hw/sai:is_fake": [],
})

# Matches common_srcs from Meta's api.bzl
_COMMON_SRCS = [
    "AddressUtil.cpp",
    "FdbApi.cpp",
    "SaiAttribute.cpp",
    "HashApi.cpp",
    "LoggingUtil.cpp",
    "MplsApi.cpp",
    "NeighborApi.cpp",
    "NextHopGroupApi.cpp",
    "PortApi.cpp",
    "QosMapApi.cpp",
    "RouteApi.cpp",
    "SaiApiLock.cpp",
    "Srv6Api.cpp",
    "SaiApiTable.cpp",
    "SwitchApi.cpp",
    "SystemPortApi.cpp",
    "Types.cpp",
]

# Matches brcm_srcs from Meta's api.bzl
_BRCM_SRCS = _COMMON_SRCS + [
    "bcm/AclApi.cpp",
    "bcm/ArsApi.cpp",
    "bcm/ArsProfileApi.cpp",
    "bcm/DebugCounterApi.cpp",
    "bcm/NextHopGroupApi.cpp",
    "bcm/PortApi.cpp",
    "bcm/SwitchApi.cpp",
    "bcm/TamApi.cpp",
    "bcm/BufferApi.cpp",
    "bcm/QueueApi.cpp",
    "bcm/MirrorApi.cpp",
    "bcm/SystemPortApi.cpp",
    "bcm/HostifApi.cpp",
]

# Matches the else() branch in cmake/AgentHwSaiApi.cmake (no bcm/ shims).
_FAKE_SRCS = _COMMON_SRCS + [
    "fake/FakeSaiExtensions.cpp",
]

def sai_api_impl():
    """Define SAI API and traced API libraries."""

    cc_library(
        name = "sai_api",
        srcs = select({
            "//fboss/agent/hw/sai:is_bcm": _BRCM_SRCS,
            "//fboss/agent/hw/sai:is_fake": _FAKE_SRCS,
        }),
        hdrs = native.glob(["*.h"]) + native.glob(["fake/*.h"]),
        copts = _SAI_COPTS,
        deps = [
            ":address_util",
            ":sai_types",
            "//fboss/agent:fboss-error",
            "//fboss/agent:fboss-types",
            "//fboss/lib:function_call_time_reporter",
            "//fboss/lib:hw_write_behavior",
            "@folly//:folly",
            "@libsai//:libsai",
        ],
        visibility = ["//visibility:public"],
    )

    cc_library(
        name = "sai_traced_api",
        copts = _SAI_COPTS,
        deps = [
            ":sai_api",
            "//fboss/agent/hw/sai/tracer:sai_tracer",
        ],
        visibility = ["//visibility:public"],
    )
