// Copyright 2004-present Facebook. All Rights Reserved.

#include "fboss/agent/hw/sai/switch/SaiSwitchManager.h"

#if defined(BRCM_SAI_SDK_XGS_GTE_15_0)
#include "fboss/agent/hw/sai/switch/DropReasonUtils.h"

#include <folly/Conv.h>
#include <folly/logging/xlog.h>

#include <algorithm>
#include <iterator>
#include <span>
#include <string>
#include <string_view>

extern "C" {
#include <experimental/saidropextensions.h>
}
#endif

namespace facebook::fboss {

void publishSwitchWatermarks(HwSwitchWatermarkStats& /*watermarkStats*/) {}

void publishSwitchPipelineStats(HwSwitchPipelineStats& /*pipelineStats*/) {}

void publishSwitchTemperatureStats(
    HwSwitchTemperatureStats& /*temperatureStats*/) {}

#if defined(BRCM_SAI_SDK_XGS_GTE_15_0)
namespace {

// sai_packet_drop_type_{ingress,egress}_t from saidropextensions.h, in
// declaration order without the START/END markers. The static_asserts below
// catch header drift.
#define FBOSS_BCM_INGRESS_DROP_TYPES(X) \
  X(NONE)                               \
  X(ALL)                                \
  X(CML_FLAGS_DROP)                     \
  X(L2_SRC_STATIC_MOVE)                 \
  X(L2_SRC_DISCARD)                     \
  X(MACSA_MULTICAST)                    \
  X(OUTER_TPID_CHECK_FAILED)            \
  X(INCOMING_PVLAN_CHECK_FAILED)        \
  X(PKT_INTEGRITY_CHECK_FAILED)         \
  X(PROTOCOL_PKT_DROP)                  \
  X(MEMBERSHIP_CHECK_FAILED)            \
  X(SPANNING_TREE_CHECK_FAILED)         \
  X(L2_DST_LOOKUP_MISS)                 \
  X(L2_DST_DISCARD)                     \
  X(L3_DST_LOOKUP_MISS)                 \
  X(L3_DST_DISCARD)                     \
  X(L3_HDR_ERROR)                       \
  X(L3_TTL_ERROR)                       \
  X(IPMC_L3_IIF_OR_RPA_ID_CHECK_FAILED) \
  X(TUNNEL_TTL_CHECK_FAILED)            \
  X(TUNNEL_OBJECT_VALIDATION_FAILED)    \
  X(TUNNEL_ADAPT_DROP)                  \
  X(PVLAN_DROP)                         \
  X(VFP)                                \
  X(IFP)                                \
  X(IFP_METER)                          \
  X(DST_FP)                             \
  X(MPLS_PROTECTION_DROP)               \
  X(MPLS_LABEL_ACTION_INVALID)          \
  X(MPLS_TERM_POLICY_SELECT_TABLE_DROP) \
  X(MPLS_RESERVED_LABEL_EXPOSED)        \
  X(MPLS_TTL_ERROR)                     \
  X(MPLS_ECN_ERROR)                     \
  X(EM_FT)                              \
  X(IVXLT)                              \
  X(EP_RECIRC_MIRROR_DROP)              \
  X(MTOP_IPV4_GATEWAY)                  \
  X(URPF_CHECK_FAILED)                  \
  X(SRC_PORT_KNOCKOUT_DROP)             \
  X(LAG_FAILOVER_PORT_DOWN)             \
  X(SPLIT_HORIZON_CHECK_FAILED)         \
  X(DST_LINK_DOWN)                      \
  X(BLOCK_MASK_DROP)                    \
  X(L3_MTU_CHECK_FAILED)                \
  X(SEQ_NUM_CHECK_FAILED)               \
  X(L3_IIF_EQ_L3_OIF)                   \
  X(STORM_CONTROL_DROP)                 \
  X(EGR_MEMBERSHIP_CHECK_FAILED)        \
  X(EGR_SPANNING_TREE_CHECK_FAILED)     \
  X(DST_PBM_ZERO)                       \
  X(MPLS_CTRL_PKT_DROP)                 \
  X(RIPD4)                              \
  X(RIPC4)                              \
  X(RIPHE4)                             \
  X(IMRP4)                              \
  X(RIPD6)                              \
  X(RIPC6)                              \
  X(RIPHE6)                             \
  X(IMRP6)                              \
  X(RDISC)                              \
  X(RUC)                                \
  X(RPORTD)                             \
  X(PDISC)                              \
  X(IMBP)                               \
  X(RFILDR)                             \
  X(RIMDR)                              \
  X(RDROP)                              \
  X(IRPSE)                              \
  X(IRHOL)                              \
  X(IRIBP)                              \
  X(DSL3HE)                             \
  X(IUNKHDR)                            \
  X(DSL4HE)                             \
  X(IMIRROR)                            \
  X(DSICMP)                             \
  X(DSFRAG)                             \
  X(MTUERR)                             \
  X(RTUN)                               \
  X(RTUNE)                              \
  X(VLANDR)                             \
  X(RHGUC)                              \
  X(RHGMC)                              \
  X(MPLS)                               \
  X(MACLMT)                             \
  X(MPLSERR)                            \
  X(URPFERR)                            \
  X(HGHDRE)                             \
  X(MCIDXE)                             \
  X(LAGLUP)                             \
  X(LAGLU_PD)                           \
  X(PARITYD)                            \
  X(VFPDR)                              \
  X(URPF)                               \
  X(DSTDISCARDDROP)                     \
  X(CLASSBASEDMOVEDROP)                 \
  X(MACLMT_NODROP)                      \
  X(MACSAEQUALMACDA)                    \
  X(MACLMT_DROP)                        \
  X(RX_SYMBOL)                          \
  X(TIME_ALIGNMENT_EVEN)                \
  X(TIME_ALIGNMENT_ODD)                 \
  X(BIT_INTERLEAVED_PARITY_EVEN)        \
  X(BIT_INTERLEAVED_PARITY_ODD)         \
  X(FCM_PORT_CLASS3_RX)                 \
  X(FCM_PORT_CLASS3_RX_DISCARDS)        \
  X(FCM_PORT_CLASS2_RX)                 \
  X(FCM_PORT_CLASS2_RX_DISCARDS)        \
  X(NON_HGOE)                           \
  X(HGOE)                               \
  X(VNTAG_RX_ERROR)                     \
  X(NIV_RX_FORWARDING_ERROR)            \
  X(IFP_TRIGGER_PFC_RX)                 \
  X(HIGIG_LOOPBACK_DROP)                \
  X(HIGIG_UNKNOWN_OPCODE_DROP)          \
  X(IPINIP_DROP)                        \
  X(MIM_DROP)                           \
  X(TUNNEL_INTERFACE_ERROR_DROP)        \
  X(MPLS_CONTROL_WORD_INVALID)          \
  X(MPLS_GAL_NOT_BOS)                   \
  X(MPLS_PAYLOAD_INVALID)               \
  X(MPLS_ENTROPY_DROP)                  \
  X(MPLS_LABEL_LOOKUP_MISS)             \
  X(MPLS_ACTION_INVALID)                \
  X(TUNNEL_SHIM_ERROR)                  \
  X(VLAN_MISMATCH)                      \
  X(VLAN_MEMBER_MISMATCH)               \
  X(TPID_MISMATCH)                      \
  X(PRIVATE_VLAN_MISMATCH)              \
  X(MAC_IP_BIND_ERROR)                  \
  X(VLAN_TRANSLATE2_LOOKUP_MISS)        \
  X(L3_TUNNEL_LOOKUP_MISS)              \
  X(MPLS_LOOKUP_MISS)                   \
  X(VLAN_TRANSLATE1_LOOKUP_MISS)        \
  X(FCOE_VFT_DROP)                      \
  X(FCOE_SRC_BIND_ERROR)                \
  X(FCOE_SRC_FPMA_ERROR)                \
  X(VFI_P2P_DROP)                       \
  X(COMPOSITE_ERROR)                    \
  X(BPDU_DROP)                          \
  X(PROTOCOL_DROP)                      \
  X(UNKNOWN_MAC_SA_DROP)                \
  X(SRC_ROUTE_DROP)                     \
  X(L2_DST_DISCARD_DROP)                \
  X(L3_DISABLE_DROP)                    \
  X(MAC_SA_EQUAL_0_DROP)                \
  X(VLAN_CROSSCONNECT_NON_UNICAST)      \
  X(TIME_SYNC_DROP)                     \
  X(IPMC_DROP)                          \
  X(MY_STATION_DROP)                    \
  X(PRIVATE_VLAN_VP_FILTER_DROP)        \
  X(TUNNEL_DECAP_ECN_ERROR)             \
  X(L3_SRC_DISCARD_DROP)                \
  X(FCOE_ZONE_LOOKUP_MISS)              \
  X(L2_HEADER_ERROR)                    \
  X(L2_TTL_ERROR)                       \
  X(L2_RPF_ERROR)                       \
  X(TAG_UNTAG_DISCARD_DROP)             \
  X(FCOE_ZONE_ERROR)                    \
  X(FIELD_CHANGE_L2_NO_REDIRECT)        \
  X(NEXT_HOP_DROP)                      \
  X(NAT_DROP)                           \
  X(DLB_RH_RESOLUTION_ERROR)            \
  X(MAC_CONTROL_DROP)                   \
  X(PROTOCOL_ERROR_IP4)                 \
  X(PROTOCOL_ERROR_IP6)                 \
  X(LAG_FAIL_LOOPBACK)                  \
  X(ECMP_RESOLUTION_ERROR)              \
  X(PFM_DROP)                           \
  X(TUNNEL_ERROR)                       \
  X(BFD_UNKNOWN_ACH_ERROR)              \
  X(BFD_UNKNOWN_CONTROL_FRAMES)         \
  X(BFD_UNKNOWN_VERSION_DISCARDS)       \
  X(DSL2HE)                             \
  X(EGRESS_MASK_DROP)                   \
  X(FIELD_REDIRECT_MASK_DROP)           \
  X(FIELD_DELAY_DROP)                   \
  X(EGRESS_MASK_SRC_PORT_DROP)          \
  X(MAC_BLOCK_MASK_DROP)                \
  X(MC_ERROR)                           \
  X(NON_UNICAST_MASK_DROP)              \
  X(NON_UNICAST_LAG_MASK_DROP)          \
  X(STG_MASK_DROP)                      \
  X(VLAN_BLOCK_MASK_DROP)               \
  X(EGRESS_VLAN_MEMBER_MISMATCH)        \
  X(NEXT_HOP_L3_EIF_RANGE)              \
  X(VXLAN_DECAP_SRC_IP_LOOKUP)          \
  X(LINK_DOWN)                          \
  X(PARTIAL_LINK_DOWN)                  \
  X(VXLAN_VFI_ASSIGN_FAIL)              \
  X(VXLAN_TUNNEL_ERROR)                 \
  X(ECMP_PROTECTION_COLLISION)          \
  X(INT_MTU_ERROR)                      \
  X(ECMP_MEMBER_NOT_RESOLVED)           \
  X(NON_FIRST_PASS)                     \
  X(ECMP_PROTECTION_MEMBER_ACTIVE)      \
  X(STATEFUL_MOD_SECOND_PASS)           \
  X(HIGIG3_DROP)                        \
  X(NON_HIGIG3_DROP)                    \
  X(L2_TUNNEL_SVP_ASSIGN_FAIL)          \
  X(SRV6_PROCESS_ERROR)                 \
  X(SRV6_VALIDATION_ERROR)              \
  X(SRV6_UNKNOWN_ROUTING_TYPE)          \
  X(SVTAG_LOOKUP_MISS)                  \
  X(IFA_DROP)                           \
  X(UDF_DROP)                           \
  X(DR_DROP)                            \
  X(VLAN_TO_VRF_MISS)                   \
  X(INC_ERROR)                          \
  X(AFR_TTL_ERROR)                      \
  X(AFR_DST_LOOKUP)                     \
  X(AFR_DST_DISCARD)                    \
  X(DR_SAME_PORT_CHECK_FAIL)            \
  X(DR_LINK_DOWN)                       \
  X(AFR_PKT)                            \
  X(L2_INSTR_DROP)                      \
  X(AR_NO_DESTINATION_DROP)             \
  X(L2_VLAN_TENANT_DROP)                \
  X(IP_ROUTED_VLAN_TENANT_DROP)         \
  X(AFR_VLAN_TENANT_DROP)               \
  X(AR_VC_DROP)                         \
  X(INC_POLICY_DROP)                    \
  X(INC_EVENT_PACKETS)                  \
  X(AFR_VLAN_TO_VRF_MISS)               \
  X(INVALID_UEC_TYPE_DROP)              \
  X(APU_DROP)                           \
  X(PDN_DROP)                           \
  X(FAILOVER_TO_AR)                     \
  X(NON_SWITCH_COPY_LINK_DOWN)          \
  X(L3_UNKNOWN_HEADER)                  \
  X(MC_PARITY_ERROR)                    \
  X(MC_ZERO_BITMAP)                     \
  X(MPLS_SEQ_NUMBER_ERROR)

#define FBOSS_BCM_EGRESS_DROP_TYPES(X) \
  X(NONE)                              \
  X(ALL)                               \
  X(L2_OIF)                            \
  X(MEMBERSHIP)                        \
  X(DVP_MEMBERSHIP)                    \
  X(TTL)                               \
  X(L3_SAME_INTF)                      \
  X(L2_SAME_PORT)                      \
  X(SPLIT_HORIZON)                     \
  X(STG_DISABLE)                       \
  X(STG_BLOCK)                         \
  X(EFP)                               \
  X(EGR_METER)                         \
  X(EGR_MTU)                           \
  X(EGR_VXLT)                          \
  X(EGR_CELL_TOO_LARGE)                \
  X(EGR_CELL_TOO_SMALL)                \
  X(QOS_REMARKING)                     \
  X(SVP_EQUAL_DVP)                     \
  X(INVALID_1588_PKT)                  \
  X(FLEX_EDITOR)                       \
  X(EP_RECIRC)                         \
  X(IFA_MD_DELETE)                     \
  X(TGIP4)                             \
  X(TIPD4)                             \
  X(TGIPMC4)                           \
  X(TIPMCD4)                           \
  X(TGIP6)                             \
  X(TIPD6)                             \
  X(TGIPMC6)                           \
  X(TIPMCD6)                           \
  X(TTNL)                              \
  X(TTNLE)                             \
  X(TTTLD)                             \
  X(TCFID)                             \
  X(TVLAN)                             \
  X(TVLAND)                            \
  X(TVXLTMD)                           \
  X(TSTGD)                             \
  X(TAGED)                             \
  X(TL2MCD)                            \
  X(TPKTD)                             \
  X(TMIRR)                             \
  X(TSIPL)                             \
  X(THGUC)                             \
  X(THGMC)                             \
  X(THIGIG2)                           \
  X(THGI)                              \
  X(TL2_MTU)                           \
  X(TPARITY_ERR)                       \
  X(TIP_LEN_FAIL)                      \
  X(TMTUD)                             \
  X(TSLLD)                             \
  X(TL2MPLS)                           \
  X(TL3MPLS)                           \
  X(TMPLS)                             \
  X(TMODIDTOOLARGEDROP)                \
  X(PKTMODTOOLARGEDROP)                \
  X(FCM_PORT_CLASS3_TX)                \
  X(FCM_PORT_CLASS2_TX)                \
  X(ECN_TX_ERROR)                      \
  X(NIV_TX_PRUNE)                      \
  X(FWD_DOMAIN_NOT_FOUND)              \
  X(NOT_FWD_DOMAIN_MEMBER)             \
  X(NON_UNICAST_PRUNE)                 \
  X(SVP_REMOVE)                        \
  X(VPLAG_PRUNE)                       \
  X(MMU_PURGE)                         \
  X(EGRESS_PORT_DROP)                  \
  X(EGRESS_FILTER_DROP)                \
  X(VISIBILITY_DROP)                   \
  X(LOOPBACK_TO_LOOPBACK_DROP)         \
  X(INT_DATAPLANE_PROBE_DROP)          \
  X(INT_VECTOR_MISMATCH)               \
  X(VFI_ADAPT_LOOKUP_MISS)             \
  X(ADAPT_LOOKUP_MISS)                 \
  X(SVP_ES_DROP)                       \
  X(DCN_PKT_ROUTING_PLANE_MAP)         \
  X(IFA_ACTION_NOT_APPLIED)            \
  X(NON_FIRST_PASS)                    \
  X(EP_RECIRC_DROP)                    \
  X(IFA_TERM_MIRROR_COPY_SUPPRESS)     \
  X(EP_RECIRC_SUPRESS)                 \
  X(COMPOSITE_ERR)                     \
  X(INC_ERROR)                         \
  X(INC_ACK_SUPPRESSION)               \
  X(INC_POLICY_DROP)                   \
  X(CONGESTIONS)                       \
  X(NEW_PKT_ECN_ILLEGAL_KEY)           \
  X(IFA_TERM_ERROR)                    \
  X(MPB_SIZE32)                        \
  X(MPB_SIZE40)                        \
  X(ES_FILTER_DROP)                    \
  X(SRV6_ES_ID_MISS)                   \
  X(APU_DROP)                          \
  X(FLEX_INSTR_ACTION_NOT_APPLIED)     \
  X(TRIM_ERROR_DROP)                   \
  X(DATA_PATH_INTF_ERROR)              \
  X(VLAN_MEMBER_FILTER)                \
  X(PARSE_DEPTH_LIMIT_EXCEED)          \
  X(IFA_PROBE_INIT_ERROR)              \
  X(DCN_TUNNEL_INHERIT_ERROR)          \
  X(AGE_DROP)                          \
  X(L2_TUNNEL_ENCAP_ADAPT_MISS)        \
  X(IPMC_L2_SELF_PORT)                 \
  X(HIGIG3_PKT_DROP)                   \
  X(NON_HIGIG3_PKT_DROP)               \
  X(INT_PROBE_TERMINATION)             \
  X(DCN_DROP_TUNNEL_TERM_INHERIT)      \
  X(AFR_VLAN_TENANT_DROP)              \
  X(IP_ROUTED_VLAN_TENANT_DROP)        \
  X(L2VLAN_TENANT_DROP)                \
  X(PROTECTION_DATA_DROP)              \
  X(L3_EGRESS_OR_INTF_RANGE)           \
  X(BAD_TPID)                          \
  X(INT_OVERFLOW)                      \
  X(PKT_TOO_SMALL)                     \
  X(TUNNEL_SNAP)

struct DropTypeName {
  sai_int32_t value;
  std::string_view name;
};

#define FBOSS_INGRESS_DROP_TYPE_NAME(name) \
  DropTypeName{SAI_PACKET_DROP_TYPE_INGRESS_##name, #name},
#define FBOSS_EGRESS_DROP_TYPE_NAME(name) \
  DropTypeName{SAI_PACKET_DROP_TYPE_EGRESS_##name, #name},

constexpr DropTypeName kIngressDropTypeNames[] = {
    FBOSS_BCM_INGRESS_DROP_TYPES(FBOSS_INGRESS_DROP_TYPE_NAME)};
constexpr DropTypeName kEgressDropTypeNames[] = {
    FBOSS_BCM_EGRESS_DROP_TYPES(FBOSS_EGRESS_DROP_TYPE_NAME)};

#undef FBOSS_INGRESS_DROP_TYPE_NAME
#undef FBOSS_EGRESS_DROP_TYPE_NAME
#undef FBOSS_BCM_INGRESS_DROP_TYPES
#undef FBOSS_BCM_EGRESS_DROP_TYPES

template <size_t N>
constexpr bool indexedByValue(const DropTypeName (&names)[N]) {
  for (size_t i = 0; i < N; ++i) {
    if (names[i].value != static_cast<sai_int32_t>(i)) {
      return false;
    }
  }
  return true;
}

static_assert(
    std::size(kIngressDropTypeNames) == SAI_PACKET_DROP_TYPE_INGRESS_END &&
    indexedByValue(kIngressDropTypeNames));
static_assert(
    std::size(kEgressDropTypeNames) == SAI_PACKET_DROP_TYPE_EGRESS_END &&
    indexedByValue(kEgressDropTypeNames));

// RX debug counter triggers that also match forwarded traffic (RUC = good
// unicast, RIPC6 = good L3 IPv6, ...). They accompany any drop without saying
// why, so they are not logged.
constexpr sai_int32_t kIngressTrafficTypes[] = {
    SAI_PACKET_DROP_TYPE_INGRESS_RIPC4,
    SAI_PACKET_DROP_TYPE_INGRESS_IMRP4,
    SAI_PACKET_DROP_TYPE_INGRESS_RIPC6,
    SAI_PACKET_DROP_TYPE_INGRESS_IMRP6,
    SAI_PACKET_DROP_TYPE_INGRESS_RUC,
    SAI_PACKET_DROP_TYPE_INGRESS_IMBP,
    SAI_PACKET_DROP_TYPE_INGRESS_IRPSE,
    SAI_PACKET_DROP_TYPE_INGRESS_IMIRROR,
    SAI_PACKET_DROP_TYPE_INGRESS_RTUN,
    SAI_PACKET_DROP_TYPE_INGRESS_RHGUC,
    SAI_PACKET_DROP_TYPE_INGRESS_RHGMC,
    SAI_PACKET_DROP_TYPE_INGRESS_MPLS,
    SAI_PACKET_DROP_TYPE_INGRESS_MACLMT_NODROP,
};

template <size_t N>
void logDropReasonList(
    std::string_view stage,
    const std::vector<sai_int32_t>& reasons,
    const DropTypeName (&names)[N],
    std::span<const sai_int32_t> skip = {}) {
  std::vector<std::string> decoded;
  for (auto reason : reasons) {
    if (std::find(skip.begin(), skip.end(), reason) != skip.end()) {
      continue;
    }
    if (reason >= 0 && static_cast<size_t>(reason) < N) {
      decoded.emplace_back(names[reason].name);
    } else {
      decoded.push_back(folly::to<std::string>("UNKNOWN_", reason));
    }
  }
  for (const auto& line : formatDropReasonLines(decoded)) {
    XLOG(INFO) << "DROP reasons " << stage << ": " << line;
  }
}

} // namespace

void logDropReasons(
    const std::vector<sai_int32_t>& ingressDropReasons,
    const std::vector<sai_int32_t>& egressDropReasons) {
  logDropReasonList(
      "ingress",
      ingressDropReasons,
      kIngressDropTypeNames,
      kIngressTrafficTypes);
  logDropReasonList("egress", egressDropReasons, kEgressDropTypeNames);
}
#else
void logDropReasons(
    const std::vector<sai_int32_t>& /*ingressDropReasons*/,
    const std::vector<sai_int32_t>& /*egressDropReasons*/) {}
#endif

} // namespace facebook::fboss
