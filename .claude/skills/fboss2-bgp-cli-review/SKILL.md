---
name: fboss2-bgp-cli-review
description: Consumer locator for `fboss2-dev config/delete protocol bgp` reviews. bgpd (BGP++) lives outside this repo, so the generic fboss2-cli-review checks cannot Grep for the reader; this skill says which repo and files hold the bgpd config resolution, route limits, policy evaluation and thrift schemas, and how to reach them from the reviewer. Load together with fboss2-cli-review, which holds every check.
when_to_use: |
  A diff touches `fboss/cli/fboss2/commands/config/protocol/bgp/**`,
  `fboss/cli/fboss2/commands/delete/protocol/bgp/**`, `fboss/cli/fboss2/tools/bgp_json_to_cli.py`
  or its tests, or the BGP config unit / integration tests. Apply the `fboss2-cli-review`
  checks; use this skill only to find the consumer they ask you to read.
---

# fboss2 BGP CLI review (consumer locator)

The checks live in `fboss2-cli-review`. This file only answers its section 0 question,
"where is the consumer", for bgpd.

## Where the consumer lives

bgpd (BGP++) is **not** in the fboss checkout. Look, in order:

1. `../private-BGP/` or `../BGP/` next to the checkout (present when the workflow cloned it, or
   when reviewing inside the `nh` monorepo).
2. Otherwise fetch the specific files below with `mcp__github__get_file_contents` from
   `nexthop-ai/private-BGP` at `main`. Fetch only the files the diff's fields lead you to;
   each fetch is a round-trip.

| What | Path in private-BGP |
|---|---|
| Config load, peer-to-group resolution (`getValue`), `resolveCascadedAsn`, `is_passive`, `parseLinkBandwidth` | `neteng/fboss/bgp/cpp/config/Config.cpp` |
| Second hop for check A2: `getPeeringParamsHelper` copies the resolved peer config into `PeeringParams`; a field that stops in `BgpCommonPeerGroupConfig` and never reaches `PeeringParams` is read but not consumed | `neteng/fboss/bgp/cpp/config/Config.cpp`, `neteng/fboss/bgp/cpp/config/ConfigStructs.h` |
| Route limits: `capRoutesPerPeer` | `neteng/fboss/bgp/cpp/adjrib/AdjRibIn.cpp`, `adjrib/AdjRib.h` |
| Wire widths for check A6 (hold time, GR restart time) | `neteng/fboss/bgp/cpp/lib/BgpMessageSerializer.cpp` |
| Link-bandwidth constants (`kAutoLbwBps`) | `neteng/fboss/bgp/cpp/common/Consts.h` |
| Policy evaluation, link-bandwidth parsing | `neteng/fboss/bgp/cpp/policy/PolicyUtils.cpp` |
| Config schema | `configerator/structs/neteng/fboss/bgp/bgp_config.thrift` |
| Policy schema | `configerator/structs/neteng/bgp_policy/thrift/bgp_policy.thrift` |

Service-side assertion for check B1: bgpd's `getRunningConfig` thrift RPC, reached from tests
via `ConfigBgpTestBase::readRunningBgpConfigViaRpc`. `readBgpSessionConfig` and
`readSystemBgpConfig` only prove what the CLI wrote to disk.

If neither route to the source works, say so in the review body and mark every group-A
finding unverified.
