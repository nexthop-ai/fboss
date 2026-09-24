---
name: fboss2-cli-review
description: Generic review checklist for `fboss2-dev config` / `delete` CLI changes under `fboss/cli/fboss2/`. Verifies that every thrift field the CLI writes is read and meaningfully consumed by the target service, that integration tests prove the CLI-to-service interaction rather than the staged session file, and that config/delete semantics match the consumer. Area skills (e.g. fboss2-bgp-cli-review) only say where a service's consumer code lives; this skill holds every check. Attached to the AI reviewer via .github/REVIEWERS; also usable by hand before pushing.
when_to_use: |
  A diff touches `fboss/cli/fboss2/commands/config/**`, `fboss/cli/fboss2/commands/delete/**`,
  `fboss/cli/fboss2/session/**`, or the fboss2 config unit / integration tests. The AI review
  workflow loads it automatically for those paths; a developer can read it before opening a
  config-CLI PR. When the diff is under `commands/{config,delete}/protocol/bgp/`, the
  `fboss2-bgp-cli-review` skill is loaded as well and says where the bgpd consumer lives.
---

# fboss2 config CLI review (generic)

The generic FBOSS reviewers (`fboss/skills/fboss-review`) have no CLI coverage. Every rule here
comes from a review thread a human reviewer actually raised on an fboss2 config-CLI PR, so treat
each check as a bug class that has shipped before, not as a style preference.

The core idea: a config CLI is a **writer** to a thrift struct that some **service** reads.
The diff shows the writer. Almost every real bug is in the gap between what the writer stores
and what the reader does with it. Read the reader before judging the writer.

## 0. Locate the consumer

| CLI area | Service | Consumer entry point |
|---|---|---|
| `commands/config/**` SwitchConfig attributes (port, vlan, interface, qos, acl, copp, ...) | wedge_agent | `fboss/agent/ApplyThriftConfig.cpp` and the switch-state object it builds; `fboss/agent/switch_config.thrift` |
| `commands/{config,delete}/protocol/bgp/**` | bgpd | see `fboss2-bgp-cli-review` (source lives outside this repo) |
| `session/**` | all | `fboss/cli/fboss2/session/ConfigSession.cpp` commit path, `FbossServiceUtil::restartTypeName`, per-service action-level handling |

If an area skill is loaded, use its consumer table for that area. If the consumer's source is
not reachable, say so in the review body and mark every group-A finding unverified (confidence
below 0.7, so it is listed as dropped rather than posted).

## How to run these checks

Work from the handler's **attribute list**: every `set`/`reset` row in the area's attribute
registry table and every thrift field it touches. Build that list first with Grep, then run
groups A to E against it. A check with nothing to report records "none". Anchor findings at the
setter line that writes the field (not the registry row that names it); anchor "missing"
findings (no test, no BUCK entry) as a file-level comment on the handler. A consumer fact the
PR body asserts that the consumer source contradicts raises the finding's confidence; it is not
a separate E finding.

Severity guide: group A and B = HIGH unless stated; C = MEDIUM; D and E = LOW/MEDIUM.

## A. Consumer contract — is the field read, and does the read mean something?

**A1. Every field the CLI writes has a reader.** For each thrift field in the attribute list,
grep the consumer for a read of that field. No reader = dead config: the CLI reports success
and nothing changes. Flag it HIGH. Precedent: `needL2Entry`, `proactiveArp`, `arpRefresh`,
`maxRouteCounterIDs` were all added as CLI attributes before anyone checked the agent reads them.

**A2. The read is meaningful.** Follow the value from the read to the point where it changes
behaviour: a state-object field the HwSwitch programs, a SAI attribute, a session FSM input, a
policy evaluation. A field that is parsed and stored, or only echoed back in `getRunningConfig`,
does not count. Say in the finding where the trace stopped.

**A3. Deprecated fields win when the consumer still dispatches on them.** When a struct carries
both a deprecated field and its replacement, read the consumer's switch, not the thrift comment.
Writing only the new field is a silent no-op; writing both inconsistently is worse.

**A4. Optional-struct defaults and inheritance are preserved.** Any `ensure()` / emplace on an
optional sub-struct, followed by setting one member, silently resets every other member to its
thrift default. If the consumer resolves the struct as a whole (parent-to-child inheritance,
profile fallback), the CLI must seed from the inherited or existing value first, or write an
explicit "disabled" value. Look for `ensure()` immediately followed by a single assignment.
Before judging any child override, find the consumer's resolution function and state its
granularity (whole struct or per field) in the finding.

**A5. Enum and boolean semantics match the consumer.** Read the consumer's `switch` or `if`
on the enum before accepting a CLI option name. A CLI keyword that promises a mode the consumer
cannot express, or a boolean whose `false` the consumer reads as "both", is a finding. An enum
or bitmask with no "off" member, where clearing the child value falls back to the parent, means
the CLI's `false`/`reset` must write an explicit value, not clear the field. Action
levels mean something different per (service, level): see `FbossServiceUtil::restartTypeName`.

**A6. Ranges are validated where the consumer wraps or rejects.** Check the wire width and any
consumer-side clamp. The thrift type being `i32` proves nothing: find where the value is
serialised or programmed (the wire encoder, the SAI attribute) and read the field width there;
a consumer that only rejects negatives still wraps 65536 to 0 on a 16-bit field. Also check
values the protocol accepts but that never work (a hold time of 1 or 2). The CLI must reject
out-of-range values before they reach the session file.

**A7. Keys are normalised the way the consumer indexes them.** Prefixes masked, names trimmed
or case-handled the way the consumer looks them up. Compare the masking flag on both sides
explicitly (`createNetwork(..., applyMask)` in the CLI normaliser against the consumer's); a
CLI that keeps host bits while the consumer masks treats `10.0.0.1/24` and `10.0.0.2/24` as two
objects the consumer sees as one. Otherwise `config` creates a duplicate and `delete` misses.

**A8. Parsers agree.** If the consumer has its own parser for a value format, the CLI must
accept the same grammar or reuse the parser. Otherwise a valid existing config cannot be
recreated through the CLI.

**A9. Absent-struct semantics.** Check what the consumer does when a struct is missing
entirely. A `delete`/`reset` that drops the struct must land the operator on the default they
expect, not a different one.

## B. Integration tests prove CLI-to-service interaction

**B1. The test asserts on the service's view.** After `commit`, the assertion must go through
the target service: the agent's `Fboss2IntegrationTest::getRunningConfig()` / switch state,
`show hw-object`, or the area skill's equivalent RPC. A test that only reads the staged session
file back is a unit test in the wrong directory. Flag any new integration test whose assertions
never touch the service.

**B2. Every attribute has a commit-level test.** Diff the handler's attribute list against the
`ConfigXTest.cpp` / `DeleteXTest.cpp` in `test/integration_test/`. Untested attributes are a
file-level finding; name them.

**B3. Inheritance and override are tested.** For any struct in A4, require a test with the
parent value set and the child overriding or clearing it, asserting the resolved value on the
service side.

**B4. Teardown restores the service.** Tests inherit `Fboss2IntegrationTest` and rely on the
baseline record/rollback; a test that leaves config behind or depends on suite order is a
finding.

**B5. Restart levels are exercised.** If the attribute's action level is SERVICE_RESTART or
DISRUPTIVE_SERVICE_RESTART, the test must survive the restart and re-assert on the service
afterwards. Asserting the level string alone proves nothing.

## C. CLI structure and behaviour

**C1. Messages state what happened.** "Successfully created X" when X already existed, or
success when the consumer will ignore the write (A1), is a finding. Check the existing-object
branch of every `config` handler.

**C2. Delete checks referential integrity.** Deleting an object that something else still
references (a policy used by a peer, a QoS map used by a port, a VLAN with interfaces) must be
rejected with the referrer named, when the consumer would otherwise reject the whole config at
load and the commit crash-loops. Grep the handler for a reference scan before `erase`.

**C3. Incomplete configs cannot be committed when the consumer aborts on them.** An IpInIp
tunnel without a source IP, a PortVlanId on a recreated port: if the consumer's failure mode is
SIGABRT, the CLI must refuse to stage it.

**C4. Action level is derived from the consumer.** Check the level against what the consumer
actually does on reload: a HITLESS claim needs a `reloadConfig` path that applies the field
without restart. See `session/FbossServiceUtil.cpp` and add-config-cli section 2.

**C5. No string literals in handler code.** Attribute names, enum names and usage text come from
the registry table / generated helpers, not inline literals (established review preference).

## D. Build, schema and compatibility

**D1. BUCK and cmake both list every new source and test**, sorted, with deps for generated
thrift headers. Meta's internal import of a stack failed on a missing BUCK dep that cmake CI
never exercised. Files must appear in `fboss/cli/fboss2/BUCK` and the matching test BUCK
(`test/config/BUCK`, `test/integration_test/BUCK`, `tools/tests/BUCK`), and in the
`cmake/CliFboss2*.cmake` lists.

**D2. Thrift changes deprecate, never delete.** A removed enum value or field breaks config
files already on devices; keep the old value readable and mark it deprecated.

**D3. Upstream convergence.** If the file is mirrored upstream, the change must leave it
byte-identical to what will land in facebook/fboss; no NH device names, Jira IDs, or internal
stack references in code or committed docs.

## E. Process

**E1. Respect prior threads on both mirrors.** Fetch existing review comments on this PR *and*,
when the PR body names an upstream counterpart, skim that PR's threads; the same finding usually
applies to both and should not be re-raised.

**E2. PR body names the consumer trace.** For each new attribute the description should say
which service reads the field, where, and how that was verified on a device. A body that only
lists the CLI grammar is a LOW finding asking for the trace.

## Reporting

Use the standard fboss review table (`File:Line | Reviewer | Severity | Issue | Confidence`)
with the reviewer column set to the check id (`A4`, `B1`, ...). Only post findings you verified
against the checkout or the consumer source; a consumer trace you could not complete is listed
in the dropped section with the reason, not posted as a comment.
