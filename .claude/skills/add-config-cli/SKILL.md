---
name: add-config-cli
description: Implement a new `fboss2-dev config <area> <attr> <value>` CLI command family mapping to `SwitchConfig` attributes. Takes a JIRA ticket, figures out the correct action level (HITLESS / WARMBOOT / COLDBOOT), wires the handler through the full registration + build graph, writes unit + integration tests, runs them on a DUT, and opens a PR.
when_to_use: |
  User asks to add a new CLI command (or family of related commands) under
  `fboss2-dev config ...` that sets one or more fields on the agent's
  `SwitchConfig` object. Typical request: "implement NOS-XXXX — CLI for
  configuring <something>".
argument-hint: [JIRA] [branch] [DUT] [sample-config]
---

# Adding a new `fboss2-dev config <area>` CLI command family

## 0. Inputs

- One or more JIRA ticket numbers (e.g. `NOS-5734`) and its list of desired
  subcommands, ideally spelling out `fboss2-dev config <area> <attr> <value>`
  shape. Multiple JIRA ticket numbers are acceptable when it makes sense to
  batch together related commands. Use `acli jira workitem view <ticket>` to
  view the JIRA tickets.

  Before starting the implementation, assign the ticket(s) to the user and
  transition them to "In Progress". Do this up front so status reflects reality
  while the work is happening, not just when the PR lands:

  ```bash
  acli jira workitem assign --key "NOS-XXXX[,NOS-YYYY]" --assignee "@me" -y
  acli jira workitem transition --key "NOS-XXXX[,NOS-YYYY]" --status "In Progress" -y
  ```

  (`@me` resolves to the caller's own account; it does not require the email
  address. Use the same comma-separated key list for both commands.)

  **Note**: The JIRA ticket numbers are Nexthop-internal and must not be
  referenced anywhere in the code. The only mention should be on the first
  line of the commit message.
- **Optional**: A git branch based on `main` (e.g. `benoit.<area>-config`).
  Will be created automatically if it doesn't exist yet.
- **Optional**: a DUT name the user has already claimed + prepared (e.g.
  *"gold405 is ready, I ran `nh tb prepare --env fboss --branch main
  gold405`"*). If provided, skip the claim + prepare steps in §6 and go
  straight to the image sanity checklist. If not provided, claim one
  automatically per §6.
- **Optional but strongly preferred**: a path to a real production FBOSS
  `agent.conf` from a Meta-deployed device (e.g.
  `/tmp/sample-configs/.../agent/current`). This anchors the tests to the
  config shape the CLI must actually be able to drive in production.
  - Do **not** read the file end-to-end — production configs are hundreds
    of thousands of lines. Wait until §1, where you've identified the
    Thrift fields of interest, and then use the `Grep` tool with the
    field names (`cpuQueues`, `cpuTrafficPolicy`, `loadBalancers`, etc.)
    to locate the relevant sub-trees. Read a small window around each
    hit (≤200 lines) to capture the nested shape and any unusual
    per-field values.
  - Use what you find to shape the seed JSON in the §4 unit-test fixture
    and the target fields in the §4 integration test — so that the unit
    test proves the CLI mutates a config matching production, and the
    integration test operates on a DUT state that resembles production.
  - If the user provides a ticket like NOS-6184 with only a CLI spec and
    no sample config, ask whether one is available before falling back
    to an invented fixture — production shapes surface edge cases (union
    fields, ordered lists, optional wrappers) that synthetic fixtures
    miss.

Mirror the JIRA transition in the shared FBOSS CLI tracking spreadsheet
(see §0a) — set STATUS to `In Progress` for every row for these tickets,
and populate ETA (today + 7 days, `YYYY-MM-DD`) for any row where it's
currently empty.

## 0a. Shared FBOSS CLI tracking spreadsheet

The FBOSS team tracks CLI work in a shared Google Sheet. Each JIRA ticket
spans multiple rows (one per subcommand), so every state change must
update *all* rows for the ticket(s). The `gws` CLI is authenticated under
the user's account.

- **URL**: [config-commands tab](https://docs.google.com/spreadsheets/d/1M8ZmQlmr028ks3WqalfSsmeYGNLc3sgC1OowICAPIJs/edit?gid=1414925700)
- **Spreadsheet ID**: `1M8ZmQlmr028ks3WqalfSsmeYGNLc3sgC1OowICAPIJs`
- **Tab**: `config-commands`
- **Columns we write**: D = IMPACT (`hitless` / `warmboot` / `coldboot` —
  see §2), F = ETA (`YYYY-MM-DD`), H = STATUS, M = Upstream PR,
  N = Nexthop PR (G = NH TICKET is read-only — we match on it, never
  rewrite it)
- **Columns we *read* for context (never overwrite)** — see §1:
  O = THRIFT REFERENCE, P = JSON FIELD PATH, Q = NOTES

State-change checklist:

| Skill step | JIRA → | Spreadsheet change |
|---|---|---|
| §0 kickoff | `In Progress` | H ← `In Progress`; F ← today+7 if empty |
| §7 PR opened | `In Review` | H ← `In Review`; N ← `#NNN` hyperlink to the PR |

**Find the row range for the ticket(s)**. `gws` emits a keyring-backend
line before its JSON payload, so strip the first line before piping to
`python3`:

```bash
SHEET=1M8ZmQlmr028ks3WqalfSsmeYGNLc3sgC1OowICAPIJs
gws sheets spreadsheets values get \
    --params "{\"spreadsheetId\":\"$SHEET\",\"range\":\"config-commands!G1:G1064\"}" \
    2>&1 | tail -n +2 | python3 -c '
import sys, json
tickets = {"NOS-XXXX", "NOS-YYYY"}  # edit to match
rows = [i for i, r in enumerate(json.load(sys.stdin).get("values", []), 1)
        if r and r[0] in tickets]
print(f"{min(rows)}:{max(rows)}" if rows else "no rows")
'
```

Rows for a ticket set are always contiguous, so a single `H<min>:H<max>`
range update works. Build the `values` list with one `["In Progress"]`
entry per row:

```bash
N=<count>  # max-min+1
python3 -c "import json; print(json.dumps({'values': [['In Progress']]*$N}))" > /tmp/body.json
gws sheets spreadsheets values update \
    --params "{\"spreadsheetId\":\"$SHEET\",\"range\":\"config-commands!H<min>:H<max>\",\"valueInputOption\":\"USER_ENTERED\"}" \
    --json "$(cat /tmp/body.json)"
```

**ETA (column F)** — only fill if empty. Read F first, then update only
the rows that have no value; never overwrite an ETA the team has already
set:

```bash
ETA=$(date -d "+7 days" +%F)
gws sheets spreadsheets values get \
    --params "{\"spreadsheetId\":\"$SHEET\",\"range\":\"config-commands!F<min>:F<max>\"}" \
    2>&1 | tail -n +2 | python3 -c "
import sys, json
data = json.load(sys.stdin).get('values', [])
# emit a 1-cell update range per empty row; list of tuples (row, eta)
for i in range(<max>-<min>+1):
    cell = data[i][0] if i < len(data) and data[i] else ''
    if not cell:
        print(<min>+i)
"
# Then: one gws values update per empty row, writing $ETA to F<row>.
```

**PR link (column N)** — a `HYPERLINK` formula so the cell renders as
`#NNN` but links to the PR URL:

```bash
FORMULA='=HYPERLINK("https://github.com/nexthop-ai/private-fboss/pull/NNN","#NNN")'
python3 -c "import json; print(json.dumps({'values': [['$FORMULA']]*$N}))" > /tmp/body.json
gws sheets spreadsheets values update \
    --params "{\"spreadsheetId\":\"$SHEET\",\"range\":\"config-commands!N<min>:N<max>\",\"valueInputOption\":\"USER_ENTERED\"}" \
    --json "$(cat /tmp/body.json)"
```

`valueInputOption: USER_ENTERED` is required for the formula to be
parsed; omit it and the cell will show the raw text.

## 0b. Creating a missing JIRA ticket

If column G (NH TICKET) is **blank** for the spreadsheet row(s) you are about
to implement, create the ticket first, record the new key in column G, then
proceed with §0 (assign + transition) as normal.

Use NOS-6168 as the canonical template — same parent epic, component, priority,
and custom-field values:

| Field | Value |
|---|---|
| Project | `NOS` |
| Type | `Improvement` |
| Parent | `NOS-346` (Mosaic FBOSS CLI epic) |
| Component | `Configuration` (id `10331`) |
| Priority | `P3` |
| `customfield_10223` (NOS) | `All` (id `10086`) |
| `customfield_10322` (Customer) | `Meta` (id `10254`) |
| `customfield_10388` (FBOSS) | `FBOSS` (id `10318`) |

```bash
cat > /tmp/nos_ticket.json << 'EOF'
{
  "projectKey": "NOS",
  "summary": "Implement fboss2 config <area> <attr> ...",
  "type": "Improvement",
  "description": {
    "type": "doc", "version": 1,
    "content": [{"type": "paragraph", "content": [
      {"type": "text", "text": "<description from column C of the spreadsheet>"}
    ]}]
  },
  "parentIssueId": "NOS-346",
  "additionalAttributes": {
    "components": [{"id": "10331"}],
    "priority": {"name": "P3"},
    "customfield_10223": [{"id": "10086"}],
    "customfield_10322": [{"id": "10254"}],
    "customfield_10388": [{"id": "10318"}]
  }
}
EOF
KEY=$(acli jira workitem create --from-json /tmp/nos_ticket.json --json \
      | python3 -c "import sys,json; print(json.load(sys.stdin)['key'])")
echo "Created: $KEY"
```

When a family of commands maps to a **single ticket** (the common case for
related subcommands like `timeout`, `age-interval`, `max-probes`), use one
summary that covers the whole group (e.g.
`"Implement fboss2 config arp CLI subcommands"`).

When each subcommand has its own spreadsheet row and warrants its own ticket
(e.g. NOS-6184..NOS-6188 for the five CoPP subcommands), create one ticket
per row.

After creation, write the key back to column G of every affected row:

```bash
SHEET=1M8ZmQlmr028ks3WqalfSsmeYGNLc3sgC1OowICAPIJs
python3 -c "import json; print(json.dumps({'values': [['$KEY']]*<N>}))" > /tmp/g.json
gws sheets spreadsheets values update \
    --params "{\"spreadsheetId\":\"$SHEET\",\"range\":\"config-commands!G<min>:G<max>\",\"valueInputOption\":\"USER_ENTERED\"}" \
    --json "$(cat /tmp/g.json)" 2>&1 | tail -n +2
```

## 1. Map CLI names → Thrift fields

**First, check columns O/P/Q in the tracking spreadsheet** (§0a) for the
ticket's rows. When set, they give you the mapping directly:

- **O — THRIFT REFERENCE**: pointer into `switch_config.thrift` with struct
  (or struct.field) and line number, e.g.
  `switch_config.thrift:Fields.ipv4Fields L1703`,
  `switch_config.thrift:LoadBalancer.seed L1730`.
  Note: the line number is frequently wrong due to the thrift file changing
  frequently. The next column identifies the field name.
- **P — JSON FIELD PATH**: the path to mutate in SwitchConfig, e.g.
  `sw.loadBalancers[id=1].fieldSelection.ipv4Fields`,
  `sw.arpTimeoutSeconds`.
- **Q — NOTES**: free-form hints (e.g. deferred sub-attrs, warmboot vs
  coldboot expectations, gotchas the FBOSS reviewer flagged in a prior
  design pass). Often empty; always worth reading when set.

These columns exist because someone on the FBOSS side (or a prior author)
already did the mapping work. Skip them and you'll redo it and may miss a
gotcha called out in column Q.

If O/P are empty, fall back to reading
[fboss/agent/switch_config.thrift](../../../fboss/agent/switch_config.thrift)
directly. Example for NOS-5734 (where the skill predates the O/P columns):

| CLI attr         | SwitchConfig field       |
|------------------|--------------------------|
| `timeout`        | `arpTimeoutSeconds` (i32) |
| `age-interval`   | `arpAgerInterval` (i32)   |
| `max-probes`     | `maxNeighborProbes` (i32) |
| `stale-interval` | `staleEntryInterval` (i32)|

Either way, note the field *types* (i32 / i64 / enum / bool) — the
arg-validation code uses them.

**Now** is the time to grep the sample production config (if one was
provided in §0) for the field names you just mapped. Run
`Grep pattern="<field1>\\|<field2>" path=<sample-config>` and read a
small window (≤200 lines) around each hit to capture the nested shape,
ordering, and any unusual values. The JSON you see here is what the
unit-test seed config in §4 should mirror, and it tells you which
specific fields the integration test in §4 is most likely to find on a
real DUT.

## 2. Determine `cli::ConfigActionLevel`

For each field, answer: **can the agent apply this change at runtime, or does
it need a warmboot/coldboot?**

Check, in order:

1. `fboss/agent/ApplyThriftConfig.cpp` — find where the field is read. If
   it's just a `newSwitchSettings->set<Field>(...)` style assignment, it's
   almost certainly HITLESS. For NOS-5734, see
   [ApplyThriftConfig.cpp:5358-5384](../../../fboss/agent/ApplyThriftConfig.cpp#L5358-L5384).
   If the field is missing from `ApplyThriftConfig.cpp` entirely, it is
   **dead code in the agent** — raise this with the user before wiring the
   CLI (see §2a below).
2. `fboss/agent/hw/sai/switch/SaiSwitch.cpp` — grep for `<field>ChangeProhibited()`
   or `<field>` appearing next to a `FbossError` throw inside a
   `SwitchSettingsDelta` handler. If one exists, the field can't change
   hitlessly — use `AGENT_COLDBOOT` (or `AGENT_WARMBOOT` if the comment
   allows).
3. `fboss/agent/state/SwitchSettings.h` — the setter should be a simple
   `set<tag>(value)`. Anything more interesting means look harder.

The three action levels live in
[fboss/cli/fboss2/cli_metadata.thrift](../../../fboss/cli/fboss2/cli_metadata.thrift):
`HITLESS`, `AGENT_WARMBOOT`, `AGENT_COLDBOOT`.

**Write the determination back to column D (IMPACT) of the tracking
spreadsheet** (see §0a) — one value per row, matching the per-attribute
level you chose. Use lowercase `hitless` / `warmboot` / `coldboot` (the
existing vocabulary on that tab). Do this *overriding* whatever was
previously in column D: the value is sometimes pre-filled but has been
incorrect in the past, so treat it as a reviewer's guess, not truth.
Your own code-path investigation (ApplyThriftConfig, SaiSwitch,
SwitchSettings) is the source of truth, and the spreadsheet should
reflect what the handler actually calls `saveConfig(...)` with.

### 2a. Dead-code attributes

Some SwitchConfig fields are declared but never applied by the agent (e.g.
`arpRefreshSeconds` — in `switch_config.thrift` but not in
`switch_state.thrift` and not read by `ApplyThriftConfig.cpp`). Wiring a CLI
for these produces a no-op. Ask the user whether to:

1. Implement the CLI anyway + add a warning comment
2. Expand the PR to wire the agent side too
3. Drop that subcommand from scope and defer

NOS-5734 chose option 3 for `arpRefreshSeconds`.

## 3. Pick a structure

For a *family* of related scalar tunables on one Thrift object (like the 5
ARP timers), use a **single handler class with a `kValidAttrs` set** rather
than one class per subcommand. This is the pattern the user prefers, and
the reference implementation is
[fboss/cli/fboss2/commands/config/arp/CmdConfigArp.{h,cpp}](../../../fboss/cli/fboss2/commands/config/arp/CmdConfigArp.h).

For a single one-off command with a complex arg shape, follow
[fboss/cli/fboss2/commands/config/l2/learning_mode/CmdConfigL2LearningMode.h](../../../fboss/cli/fboss2/commands/config/l2/learning_mode/CmdConfigL2LearningMode.h).

## 4. Files to touch (family pattern)

### No string literals in handler code

The FBOSS team's code review style rejects literal string constants
sprinkled inside handler logic — lift them to named
`constexpr std::string_view` in an anonymous namespace at the top of
the `.cpp`. See
[fboss/cli/fboss2/session/FbossServiceUtil.cpp](../../../fboss/cli/fboss2/session/FbossServiceUtil.cpp)
for the canonical pattern (e.g. `kWedgeAgent`, `kSwAgent`,
`kHwAgentPrefix`). Apply the same style to every CLI attribute name
the dispatch code compares against, and build `k<Area>ValidAttrs`
from those constants rather than raw strings.

### New files

1. `fboss/cli/fboss2/commands/config/<area>/CmdConfig<Area>.h`
   - Declare only the `class <Area>ConfigArgs`, the `CmdConfig<Area>Traits`
     struct, and the `CmdConfig<Area>` handler. Do **not** put the valid-attrs
     set or the attribute-name constants in the header — keep the header
     free of implementation detail so changes to the valid-attrs list
     don't force recompiles of every TU that includes the header.
   - `class <Area>ConfigArgs : public utils::BaseObjectArgType<std::string>`
     with a `std::vector<std::string>` ctor that validates exactly 2 args,
     first ∈ valid set, second parses to a non-negative `int32_t` via
     `folly::to<int32_t>` (catch `folly::ConversionError`).
   - `struct CmdConfig<Area>Traits : public WriteCommandTraits` with
     `ObjectArgTypeId = OBJECT_ARG_TYPE_<AREA>_CONFIG`,
     `ObjectArgType = <Area>ConfigArgs`, `RetType = std::string`.
   - `class CmdConfig<Area> : public CmdHandler<CmdConfig<Area>, CmdConfig<Area>Traits>`
     declaring `queryClient(HostInfo, ObjectArgType)` + `printOutput(RetType)`.

2. `fboss/cli/fboss2/commands/config/<area>/CmdConfig<Area>.cpp`
   - `#include "fboss/cli/fboss2/CmdHandler.cpp"` — important, this is how the
     template gets instantiated
   - In an anonymous namespace at the top: one
     `constexpr std::string_view k<Area>Attr<Name>` per CLI attribute name,
     followed by `const std::set<std::string_view> k<Area>ValidAttrs = {...};`
     built from those constants.
   - `<Area>ConfigArgs` constructor body (use the constants for error
     messages + membership checks).
   - `queryClient()` body: get `ConfigSession::getInstance()`, dispatch on
     `args.getAttribute()` against the named constants (not string
     literals), mutate `config.sw()->*` fields, call
     `session.saveConfig(cli::ServiceType::AGENT, cli::ConfigActionLevel::<LEVEL>)`,
     return success string.
   - `printOutput()` → `std::cout << msg << std::endl;`
   - Trailing `template void CmdHandler<..., ...>::run();` explicit
     instantiation

3. `fboss/cli/fboss2/test/config/CmdConfig<Area>Test.cpp` — inherit
   `CmdConfigTestBase` with a seed-config JSON, test arg validation
   (valid / bad arity / unknown attr / non-integer / negative) and `queryClient()`
   for each attr. See
   [CmdConfigArpTest.cpp](../../../fboss/cli/fboss2/test/config/CmdConfigArpTest.cpp).
   - **Shape the seed JSON after the production config** (grepped from
     the §0 sample in §1). Copy enough of the sub-tree that each attr's
     `queryClient()` has something realistic to mutate: present
     optionals, populated ordered-lists, existing enum values. A
     reviewer should be able to eyeball the seed and recognize it as a
     subset of what a real device is running.
   - Cite the source in a comment at the top of the fixture
     (`// Seed mirrors rsw001_p001_m002_qzr1 near line 11076`) so a
     future reader can trace it back.

4. `fboss/cli/fboss2/test/integration_test/Config<Area>Test.cpp` — inherit
   `Fboss2IntegrationTest`; for each attr read current value via
   `getRunningConfig()` thrift, set new value with `runCli()`, `commitConfig()`,
   verify, restore. See
   [ConfigArpTest.cpp](../../../fboss/cli/fboss2/test/integration_test/ConfigArpTest.cpp).
   - Prefer helpers that *derive* targets from the live running config
     (e.g. "find the first queue that has a `pktsPerSec` cap", "use the
     reason that already maps to something") rather than hardcoding
     IDs/names. The sample config tells you which shapes to expect, and
     the running config tells you which specific values this DUT has —
     basing the test on the latter keeps it portable across DUTs.

### Modified files

| File | Change |
|---|---|
| `fboss/cli/fboss2/utils/CmdUtilsCommon.h` | Append `OBJECT_ARG_TYPE_<AREA>_CONFIG` to `ObjectArgTypeId` enum. |
| `fboss/cli/fboss2/CmdSubcommands.cpp` | Add `case OBJECT_ARG_TYPE_<AREA>_CONFIG:` → `subCmd->add_option(...)` just before the `UNINITIALIZE/NONE` cases. |
| `fboss/cli/fboss2/CmdListConfig.cpp` | Add `#include` alphabetically; add `{"config", "<area>", "…", commandHandler<CmdConfig<Area>>, argTypeHandler<CmdConfig<Area>Traits>}` to `kConfigCommandTree()` alphabetically. |
| `cmake/CliFboss2.cmake` | Add the two new source files to `fboss2_config_lib` (alphabetically). |
| `fboss/cli/fboss2/BUCK` | Mirror the cmake additions into `srcs` and `headers` of `fboss2-config-lib`. |
| `cmake/CliFboss2TestConfig.cmake` | Add unit test `.cpp` (alphabetically). |
| `fboss/cli/fboss2/test/config/BUCK` | Mirror. |
| `cmake/CliFboss2TestIntegrationTest.cmake` | Add integration test `.cpp` (alphabetically). |
| `fboss/cli/fboss2/test/integration_test/BUCK` | Mirror. (`BUILD.bazel` is auto-regenerated by `bazel.sh`; don't edit by hand.) |

## 5. Build + unit-test locally

Prefer Bazel when `fboss/oss/scripts/bazel.sh` exists on the branch:

```bash
./fboss/oss/scripts/bazel.sh build //fboss/cli/fboss2/test/config:cmd_config_test \
  //fboss/cli/fboss2/test/integration_test:fboss2_integration_test \
  //fboss/cli/fboss2:fboss2
./fboss/oss/scripts/bazel.sh test //fboss/cli/fboss2/test/config:cmd_config_test \
  --test_filter='CmdConfig<Area>TestFixture.*' --test_output=all
```

cmake fallback when `bazel.sh` is not yet on the branch:

```bash
./fboss/oss/scripts/nhfboss-build.sh --cmake-target fboss2_cmd_config_test
/var/FBOSS/tmp_bld_dir/build/fboss/fboss2_cmd_config_test \
  --gtest_filter='CmdConfig<Area>TestFixture.*'
```

## 5a. Clean up includes (mandatory before committing)

**After** the build + tests pass, **before** committing, stage the new
files and run include-cleaner over the files we changed (you must `git add`
the new files first):

```bash
git add fboss/cli/fboss2/commands/config/<area>/ \
        fboss/cli/fboss2/test/config/CmdConfig<Area>Test.cpp \
        fboss/cli/fboss2/test/integration_test/Config<Area>Test.cpp
./fboss/oss/scripts/run-clang-tool.py --include-cleaner --dirty
```

`run-clang-tool.py` self-checks whether `compile_commands.json` is
stale (older than any of the dirty files) and auto-regenerates it via
`bazel run //fboss/build_defs:refresh_compile_commands` before
invoking include-cleaner, so you don't need to run the refresh step
by hand. See `refresh_compile_commands_if_stale()` in the script.

Include-cleaner then regenerates `#include` lines in the files you've
edited — adding direct includes where a symbol was being picked up
transitively, and removing redundant ones. Re-run the build + tests
afterward.

### Recovery if you forget

```bash
./fboss/oss/scripts/run-clang-tool.py --include-cleaner --head
# then amend the commit and force-push
```

`--head` runs against the files in the tip commit, so untracked-dir
filtering doesn't apply — nothing extra to stage.

## 6. DUT integration testing

Check first: did the user already claim + prepare a DUT? They may say
something like *"gold405 is already prepped with
`nh tb prepare --env fboss --branch main gold405`"* — skip ahead to the
sanity-check step.

Otherwise:

```bash
ng tb show available          # pick a gold*/fboss*/wdg* DUT
ng tb claim --duration 2 <dut>
nh tb prepare --env fboss --branch main <dut>   # must be run by the user from an nh.git workspace, cannot be run from within an FBOSS dev container
~/bin/dut-adduser.sh <dut>
```

**DUT selection preferences**: prefer `wdgXXX` (Wedge800) or `fbossXXX`
(minipack3) DUTs first; fall back to `goldXXX` (NH-4010-F) only if
nothing else is available. If you must use a gold DUT:

- **Avoid `gold101`, `gold208`, `gold210`** — secure boot is enforced on
  these and the FBOSS image will fail to load.
- **Avoid `gold1xx` P1 units** in general — they differ enough from P2
  that they need major changes before anything will work.
- When using a `goldXXX` DUT, check that `sudo dmidecode -s system-product-name`
  returns `NH-4010-F` and not just `NH-4010`. Without the `-F` suffix the
  system won't initialize properly. Ask the user to fix the `system-product-name`
  if it's incorrect.

**DUT image sanity checklist** — freshly imaged DUTs have shipped in broken
states (see NOS-5734 work log). Before anything else, verify:

1. `ssh <dut> ls /opt/fboss/lib/ | wc -l` — should be ~hundreds, not ~6.
   If sparse, the image is missing shared libs (commonly libmvfst,
   libwangle, libfizz, libfolly, libfmt). Copy them from
   `/var/FBOSS/tmp_bld_dir/installed/*/lib{,64}/` on the dev host to
   `/opt/fboss/lib/` on the DUT.
2. `ssh <dut> sudo systemctl is-active platform_manager fboss_init fsdb qsfp_service fboss_hw_agent@0 fboss_sw_agent` — all `active`.
   If any are `failed` due to prior missing-lib crash-loops, run
   `sudo systemctl reset-failed <units> && sudo systemctl start <unit>`.
3. `ls /etc/coop/agent.conf` exists (generated by `fboss_init.sh`).
4. `ls /var/facebook/fboss/fruid.json` exists and matches the schema
   `PlatformProductInfo::parse` expects (`"Information"` wrapper, keys like
   `"System Manufacturer"`, `"Product Serial Number"`, `"Product Name"`).
   Note: `weutil --json` may emit a different schema — if
   `fboss_hw_agent@0` crashes in `PlatformProductInfo::parse`, this is likely
   the cause.
5. `sudo chgrp -R wheel /etc/coop && sudo chmod -R g+w /etc/coop` — required
   for `ConfigSession` to write to the session config without needing to run
   tests as root with `sudo`. Prefer running tests as non-root.
6. `/tmp/fboss2-dev-new show interface` succeeds without `Connection refused`.

Build + copy + run. **Two target gotchas worth calling out up front**:

- The `config` commands live in the **`fboss2-dev`** binary, not `fboss2`.
  Build and deploy `//fboss/cli/fboss2:fboss2-dev` — if you copy `fboss2`
  instead, the CLI rejects `config ...` with "The following arguments were
  not expected: ...".
- `scp` copies binaries over as mode 555. A second `scp` to the same path
  fails with `Permission denied` even for the owner. Use a fresh versioned
  filename (e.g. `fboss2-dev-nos6212f`) rather than fighting the mode.

```bash
./fboss/oss/scripts/bazel.sh build \
    //fboss/cli/fboss2:fboss2-dev \
    //fboss/cli/fboss2/test/integration_test:fboss2_integration_test
scp bazel-bin/fboss/cli/fboss2/fboss2-dev <dut>:/tmp/fboss2-dev-<ticket><suffix>
scp bazel-bin/fboss/cli/fboss2/test/integration_test/fboss2_integration_test \
    <dut>:/tmp/fboss2_it_<ticket><suffix>
ssh <dut> "/tmp/fboss2_it_<ticket><suffix> --gtest_filter='Config<Area>Test.*'"
```

Also capture an interactive session for the PR "Sample usage" — for each
attr run the CLI, then `config session diff`, then `config session commit`,
then show the relevant `show` output (or agent running config) reflecting
the new value. The reference is commit `bc4b447e2d33391bced568cb26b967a6692fc4b7`.

Release the DUT when done:

```bash
ng tb release <dut>
```

## 6a. When the CLI surfaces an agent-side crash

Integration tests exercise code paths on the agent that may have latent
bugs. The CLI correctly producing a config delta that then crashes the
agent is a common outcome — the fboss_sw_agent and fboss_hw_agent@0
processes both auto-restart under systemd, so the DUT usually recovers
even though the test reports a failure (reproduced in NOS-6213 with the
LAG `{dst-ip} → {src-ip, dst-ip}` delta).

**Find the real crash site**. The systemd core dump is typically
truncated (`coredumpctl info <pid>` shows "Storage: ... (truncated)")
and gdb without debug symbols is useless on it. Three better sources,
in order:

1. **`/var/facebook/logs/fboss/wedge_agent.log`** — the agent writes its
   full glog + the signal-handler's demangled stack trace here. Grep for
   `F<MMDD>|CHECK failed|Failed to|Terminated due to|SaiApiError`
   around the crash timestamp. This is the single most useful source —
   it includes the preceding error line (e.g.
   `[hash] Failed to remove sai object : HashSaiId(...): OBJECT IN USE`)
   which almost always names the faulty SAI call or CHECK.
2. **`sudo journalctl -u fboss_hw_agent@0 --since '<crash-time>'`** —
   useful for the process lifecycle (which process died first, when
   systemd restarted it) but the stack traces here are mostly unmangled
   thread frames with heavy idle/worker noise. Filter aggressively.
3. **gdb on the core** — if needed, `sudo dnf install -y gdb` on the
   DUT, then `sudo coredumpctl debug <pid> --debugger-arguments='-batch
   -ex "thread 1" -ex "bt"'`. Only useful when the core isn't truncated.

In the hw/sw-agent split deployment (standard on NH-4010-F), the
**hw_agent crashes first**; the sw_agent follows seconds later when it
notices the hw_agent disconnected. The sw_agent's stack trace shows an
unrelated cleanup-path abort in
`HwSwitchConnectionStatusTable::disconnected` — ignore it and focus on
the hw_agent's crash. This threw me off initially.

## 6b. Fixing an agent-side bug in the same PR

When the integration tests reveal an agent bug, decide scope:

- **Small mechanical fix (≲50 lines, clear precedent from a nearby
  working code path)**: fold it into the same commit. The NOS-6213 LAG
  hash delta crash was a missing clear-before-set in
  `SaiSwitchManager::addOrUpdateLagLoadBalancer` — the ECMP path already
  had the pattern and there was even a `TODO(skhare)` flagging the gap.
  Ported in ~20 lines, tested on the same DUT.
- **Larger or uncertain fix**: keep the CLI PR scoped, file a follow-up
  NOS ticket, disable or `GTEST_SKIP` the integration tests that
  reproduce the bug so CI doesn't core-dump the agent, and link the
  ticket from the PR.

If you include an agent fix, rebuild and redeploy the hw_agent binary:

```bash
./fboss/oss/scripts/bazel.sh build //fboss/agent/platforms/sai:fboss_hw_agent-sai_impl
scp bazel-bin/fboss/agent/platforms/sai/fboss_hw_agent-sai_impl \
    <dut>:/tmp/fboss_hw_agent-sai_impl.<suffix>
ssh <dut> "sudo systemctl stop fboss_hw_agent@0 fboss_sw_agent && \
    sudo cp /tmp/fboss_hw_agent-sai_impl.<suffix> \
            /opt/fboss/bin/fboss_hw_agent-sai_impl && \
    sudo chmod +x /opt/fboss/bin/fboss_hw_agent-sai_impl && \
    sudo systemctl start fboss_hw_agent@0 fboss_sw_agent"
```

The binary is ~1.4 GB so the scp takes 30-60 seconds on the management
network. Wait for the agent to come back up with a valid config before
re-running tests — the agent reports "switch is still initializing"
for the first few seconds:

```bash
until ssh <dut> "/tmp/fboss2-dev-<suffix> show interface 2>/dev/null | grep -q 'eth1/'"; do sleep 5; done
```

## 7. Commit + PR

Follow [.github/pull_request_template.md](../../../.github/pull_request_template.md).
First line of commit message: `NOS-XXXX: <short summary>`. Model body on
commit `bc4b447e2d33391bced568cb26b967a6692fc4b7`:

- **Summary** — what the commands do, action level, deferred pieces
- **Test Plan** — paste unit test output, integration test output, sample
  CLI transcript
- Check **Upstream required: Yes** and **PR title is free of sensitive
  information**.

Create against the internal fork:

```bash
git push -u origin <branch>
gh pr create --repo nexthop-ai/private-fboss --base main --head <branch> \
  --title "NOS-XXXX: ..." --body "$(cat <<'EOF'
...
EOF
)"
```

Note: `pre-commit` runs `clang-format` and can reformat staged files; if it
does, `git add` again and re-run the commit.

Once the PR is open:

1. Move the ticket(s) to "In Review":

   ```bash
   acli jira workitem transition --key "NOS-XXXX[,NOS-YYYY]" --status "In Review" -y
   ```

2. Mirror the transition in the tracking spreadsheet (see §0a): set
   STATUS (column H) to `In Review` for every row for these tickets,
   and fill the Nexthop PR (column N) with a `HYPERLINK` formula
   pointing at the new PR (`#NNN`).

If any design choice is deferred (e.g. a sub-attribute out of scope, as with
`udfGroups` on NOS-6212/NOS-6213), leave a comment on the ticket explaining
*why* it's deferred so reviewers don't have to reconstruct the reasoning
from the PR thread:

```bash
acli jira workitem comment create --key "NOS-XXXX[,NOS-YYYY]" --body "<explanation>"
```

## 8. Pitfalls observed

- **Forgetting to register the arg-type case** in `CmdSubcommands.cpp` — the
  command tree registers fine but argument parsing silently no-ops. Always
  add both the enum entry and the switch case.
- **Parent "branch" node must have a handler for depth to increment**
  (NOS-6184..NOS-6188). If the parent of your leaf commands in
  `CmdListConfig.cpp` has no `commandHandler`, `addCommandBranch()` does
  not increment depth, so all leaves register their positional args at
  the same `CmdArgsLists::data_[0]` slot. Give the parent a trivial
  "Incomplete command" handler (see `CmdConfigCopp`, `CmdConfigL2`, or
  `CmdConfigQos` for the pattern) and set `ParentCmd = <ParentHandler>`
  on each leaf's Traits — otherwise the first argument of a multi-token
  positional gets dropped or the wrong slot gets read.
- **CLI11 subcommand fallthrough silently reclassifies positionals**
  when an argument value happens to match a subcommand name elsewhere in
  the tree (NOS-6188). `config copp reason arp queue 0` broke because
  CLI11's `_valid_subcommand` recurses up the ancestor chain and matches
  "arp" against `config arp`, stealing it from reason's positional
  option. The fix in `CmdSubcommands.cpp` is `->required()->expected(N)`
  on the `add_option(...)` call, which makes `_parse_subcommand()` route
  the token to `_parse_positional()` instead (CLI11 checks
  `_count_remaining_positionals(required=true) > 0` before doing the
  subcommand match). Apply whenever a positional arg's value space
  overlaps with subcommand names — especially protocol names like `arp`,
  `ndp`, `bgp`, `lldp` which are subcommands of `show`, `clear`, and
  `config`.
- **Using `session.saveConfig()` without args** when the action level is not
  HITLESS — the overload defaults to `AGENT` + `HITLESS`. Always pass the
  explicit service + level pair unless HITLESS is correct.
- **Missing `#include "fboss/cli/fboss2/CmdHandler.cpp"`** in the .cpp file
  — you'll get a link error about missing `CmdHandler<...>::run()`
  instantiation.
- **`BUILD.bazel` files** in `test/integration_test/` are auto-generated by
  `bazelify.py` from `BUCK`. Edit only `BUCK`; `bazel.sh` regenerates the
  Bazel file on the next build.
- **Testing `queryClient()`, not `printOutput()`** — the skill user
  explicitly wants unit tests focused on the query/mutation side. Don't
  write tests that capture stdout from `printOutput`.
- **DUT image assumptions** — don't assume a freshly imaged DUT is actually
  healthy. Always run through the §6 sanity checklist before trying to run
  integration tests.
- **Deploying `fboss2` instead of `fboss2-dev`** — only the `-dev` binary
  has the `config` subcommand tree. The parent binary rejects `config ...`
  with `The following arguments were not expected: ...`, which reads like a
  CLI parsing bug but is really the wrong target. Always
  `bazel build //fboss/cli/fboss2:fboss2-dev` and copy the `-dev` output.
- **DUT state leaks between integration-test runs** — tests capture the
  initial state as `originalFields` / `originalValue` for restore, but a
  crash-interrupted test run leaves the DUT in whatever the last successful
  commit produced, not the pre-test baseline. The next run captures *that*
  as "original" and a hardcoded restore string can then mismatch. Prefer
  deriving restore tokens from the captured state; if you hardcode them,
  know the first run after a failure may fail for test-setup reasons
  unrelated to the code under test (just re-run once the DUT settles).
- **Truncated core dumps are useless** — `coredumpctl info <pid>` showing
  `Storage: ... (truncated)` means gdb can't recover a real backtrace. Go
  straight to `/var/facebook/logs/fboss/wedge_agent.log` instead (see §6a).
- **sw_agent crash trail is a red herring** in the hw/sw-split deployment —
  when the hw_agent dies, the sw_agent aborts seconds later inside a
  cleanup path. Focus on the hw_agent crash; the sw_agent stack won't
  point at the real bug.
