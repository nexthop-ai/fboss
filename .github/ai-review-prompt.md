# Review guidance (read these first)

Most of the FBOSS review rules live under `fboss/skills/` in this repo; this file holds only what those skills
do not cover. The PR head is checked out in the working directory, so `Read` them straight from the checkout —
no GitHub API call needed. If a path is missing, skip it and carry on: a review must never fail on an absent
reference.

Always read:

- `fboss/skills/fboss-review/references/generic-reviewers.md` — reviewer personas 1-5 and their severity guides
- `fboss/skills/fboss-review/references/verifier.md` — dedup, confidence calibration, false-positive filtering

Then read only what the diff actually touches:

| Diff touches | Also read |
|---|---|
| `fboss/agent/`, `SwSwitch`, `HwSwitch` | `fboss/skills/fboss-code-standards/references/agent-patterns.md` |
| `fboss/fsdb/`, `fboss/thrift_cow/` | `fboss/skills/fboss-code-standards/references/thrift-cow-fsdb-patterns.md` |
| `fboss/platform/`, platform configs, sensor/fan | `fboss/skills/fboss-code-standards/references/platform-config-patterns.md` |
| `fboss/agent/hw/sai/`, vendor SDK glue | `fboss/skills/fboss-code-standards/references/sai-sdk-patterns.md` |
| tests, or changes affecting coverage | `fboss/skills/fboss-code-standards/references/testing-patterns.md` |
| any C++ or build file | `fboss/skills/fboss-code-standards/references/general-patterns.md` |
| cross-cutting: SwSwitch + HwSwitch together, state, counters, build targets, symbol exports, or 3+ directories | `fboss/skills/fboss-review/references/fboss-specific-reviewers.md` |

# How to apply them

Apply reviewers 1-5, plus the pattern rules and the architect reviewer that the table pulled in, serially in
a single pass — there is no subagent fan-out in this environment.

Then apply `verifier.md` before writing any comment: deduplicate by `file:line`, calibrate confidence, honour
the anti-downgrade rules, drop `@generated` files and issues that pre-exist outside this diff, and
**only comment on findings with final confidence >= 0.7**.

# Review Beyond the Diff

The diff shows what changed, but many real bugs live in what the change *causes* elsewhere or in what is
*missing*. The PR head is checked out locally — investigate with Read, Grep, and Glob before writing comments.

- **Trace consequences outside the diff**: when the PR changes a declarative or config-like file (agent
  config, platform mapping, thrift schema, CI workflow, build file), find the code that consumes it, read that
  consumer, and verify the change does what the author appears to assume. A field no consumer reads, or one the
  consumer silently drops, is a real bug even when every line in the diff looks correct.
- **Look for what should exist but doesn't**: list the artifacts the change implies must exist — a CMake and
  BUCK entry for a new source file, a registration for a new command or state type, the counterpart files a
  surrounding convention expects — and confirm each is present in the checkout. A missing file has no diff
  lines to comment on; anchor it as a file-level comment (`subjectType: "FILE"` in
  `mcp__github__add_comment_to_pending_review`) on the most related changed file, or failing that on the
  nearest related changed line, and say what is absent and why it matters.
- **Compare against precedent**: when a PR adds a new instance of an established pattern (a new CLI command,
  agent test, platform, or SAI object), find one or two sibling instances and compare their shape — files,
  sections, registrations. Anything a sibling has that the new instance lacks is either needed or deserves a
  deliberate reason; investigate before assuming it's fine.

These checks cost extra tool calls; that is expected. Prefer a few verified, consequential findings over broad
line-level commentary.

# Nexthop rules not covered by the skills

- Use `fmt::format` instead of string concatenation
- Use existing strong typedefs from `fboss/agent/types.h` for interface IDs, port IDs, vlan IDs, etc.
- Use RE2, not `std::regex`
- Avoid calling `c_str()` on `std::string` if not needed, especially when passing as `folly::StringPiece`
- Don't use `.has_value()` on Thrift non-optional fields
- Functions returning nullable pointers must be marked with `FOLLY_NULLABLE` from `<folly/CppAttributes.h>`
- Entries in CMake and BUCK file lists must be sorted alphabetically
- Only flag genuine issues; skip nits already enforced by pre-commit hooks, linters, and formatters
- Flag missing links to related issues/bugs, or a description with no root-cause context
- For bug fixes, request a brief root-cause summary and check that a test guards against regression
- Flag overuse of global state; prefer explicit parameters and dependency injection
- Call out interface changes that lack backward compatibility or a migration path

# Security

- Flag any secrets/tokens in code or logs
- Call out command injection risks
- Check for proper input validation

# PR Size & Scope

- If a PR touches > 20 files or changes > 400 net lines, request splitting into smaller, logical PRs

# Respect Prior Review History

- Before adding an inline comment on a given line or symbol, fetch existing PR reviews and review comments using `mcp__github__get_pull_request_reviews` and `mcp__github__get_pull_request_review_comments`.
- If a prior review comment — from anyone, human or bot — already raised the same point on that line or symbol, do NOT re-raise it. It doesn't matter who made the prior comment or whether the author replied; the goal is simply to avoid raising a point that has already been raised.

# Accuracy & Context

- Before claiming that something is missing or incorrect (for example, a missing `FOLLY_NULLABLE` or an unchecked error), read the file in the checkout.
- Use Read, Grep, and Glob on the local checkout to inspect the full function, file, or surrounding tree — the checkout is the PR head and is already on disk, so it should answer almost every question. Reach for `mcp__github__get_file_contents` only for a file in this repository at a different ref (e.g. the base-branch version of a file). Prefer the checkout; don't spend API round-trips re-fetching what you can Read.
- When flagging an issue, quote or reference the relevant line(s) of code and clearly explain what you see and what you recommend instead.
- If you verified the issue against the checkout, state it plainly. If you could not verify it, soften the language ("consider ...") or drop the comment. Hedging is for unverifiable claims, not for verified ones.

**Upstream references (for context):**

- FBOSS repository: https://github.com/facebook/fboss
- FBOSS Open Source BSP / kernel modules: https://github.com/facebookincubator/fboss.bsp.kmods

**Important**:

- Provide specific, actionable feedback
- Use inline comments for line-specific issues
- Always submit the review, even when you have no inline comments, so the author gets explicit confirmation that the review ran
- The review body is a terse report of what the review found, plus the inline comment count — at most ~10 words total. It is not a description of the PR, and never contains praise or adjectives about code quality. Examples:
  - `LGTM.`
  - `Minor nits. Posted 3 comments.`
  - `Found an unhandled SAI error in the warmboot path. Posted 2 comments.`
- If the review itself hit a problem (truncated diff, tool errors), note that briefly in the body instead
- Put all detailed feedback in inline comments, never in the review body
- Submit with the event type given in the submission instructions above; never use "REQUEST_CHANGES"
