// BGP Policy Types - Minimal definitions for FBOSS OSS
// Contains only the types needed by our BGP show commands

namespace cpp2 facebook.neteng.bgp_policy
namespace py neteng.bgp_policy
namespace py3 neteng.bgp_policy

// BGP Drain State
// Used by: CmdShowBgpSummary (getDrainState method)
enum DrainState {
  UNDRAINED = 0,
  DRAINING = 1,
  DRAINED = 2,
}

// BGP Policy Direction
// Used internally by bgp_thrift.thrift structs
enum DIRECTION {
  IN = 0,
  OUT = 1,
}

// Policy Statistics
// Used by: CmdShowBgpStatsPolicy (getPolicyStats method)
struct TPolicyStats {
  1: i64 routes_matched;
  2: i64 routes_rejected;
  3: optional map<string, i64> policy_counters;
}

// BGP Policies Container
// Used by: bgp_config.thrift (BgpConfig.policies field)
struct BgpPolicies {
  1: optional map<string, string> import_policies;
  2: optional map<string, string> export_policies;
  3: optional string default_import_policy;
  4: optional string default_export_policy;
}
