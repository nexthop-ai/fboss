// RIB Policy Types - Minimal stub for FBOSS OSS
// Contains only the types referenced by bgp_thrift.thrift

namespace cpp2 facebook.neteng.bgp_policy.rib_policy
namespace py neteng.bgp_policy.rib_policy
namespace py3 neteng.bgp_policy.rib_policy

// Path selector for CPS (Centralized Path Selection)
// Used in TRibEntry.active_cps_criteria
struct TPathSelector {
  1: string name;
  2: i32 priority;
  3: optional string description;
}

// Route attribute policy
// Used by setRouteAttributePolicy/getRouteAttributePolicy
struct TRouteAttributePolicy {
  1: string name;
  2: optional string config;
}

// Path selection policy
// Used by setPathSelectionPolicy/getPathSelectionPolicy
struct TPathSelectionPolicy {
  1: string name;
  2: optional list<TPathSelector> selectors;
}

// Route filter policy
// Used by setRouteFilterPolicy/getRouteFilterPolicy and TBgpPath
struct TRouteFilterPolicy {
  1: string name;
  2: optional string filter_expression;
}

// RIB policy (main policy container)
// Used by getRibPolicy and TRibPolicyStore
struct TRibPolicy {
  1: optional TRouteAttributePolicy route_attribute_policy;
  2: optional TPathSelectionPolicy path_selection_policy;
  3: optional TRouteFilterPolicy route_filter_policy;
}
