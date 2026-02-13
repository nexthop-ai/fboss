# Code Quality & FBOSS Conventions
- Only flag genuine issues (correctness, build/test failures, security, policy/regression risks)
- Avoid "nice-to-have" or stylistic nits already enforced by pre-commit hooks/linters/formatters
- Flag deviations from established naming conventions in the codebase
- Use `fmt::format` instead of string concatenation
- Use existing strong typedefs from `fboss/agent/types.h` for interface IDs, port IDs, vlan IDs, etc.
- Avoid calling `c_str()` on `std::string` if not needed, especially when passing as `folly::StringPiece`
- Don't use `.has_value()` on Thrift non-optional fields
- Functions returning nullable pointers must be marked with `FOLLY_NULLABLE` from `<folly/CppAttributes.h>`

# PR Description & Intent
- Flag mismatches between the PR title/description and the actual code changes
- Flag missing links to related issues/bugs or lack of root-cause context
- For bug fixes, request a brief root-cause summary and verify tests guard against regression
- If the PR contains multiple unrelated intents, request splitting into smaller PRs

# Code Reuse & Modularity
- Suggest extracting shared logic into reusable helpers/utilities instead of duplicating code
- Recommend small, single-responsibility functions with clear, testable interfaces
- Flag overuse of global state; recommend explicit parameters and dependency injection
- Call out if interface changes lack backward compatibility or a migration path

# Security
- Flag any secrets/tokens in code or logs
- Call out command injection risks
- Check for proper input validation

# Performance
- Call out O(n^2) work in hot paths
- Call out excessive logging in tight loops
- Be mindful of memory allocations in performance-critical code

# PR Size & Scope
- If a PR touches > 20 files or changes > 400 net lines, request splitting into smaller, logical PRs

# Build System
- This project uses both CMake and BUCK; changes to CMake files must be reflected in corresponding BUCK files
- Ensure files are listed alphabetically in build files

**Upstream references (for context):**
- FBOSS repository: https://github.com/facebook/fboss
- FBOSS Open Source BSP / kernel modules: https://github.com/facebookincubator/fboss.bsp.kmods

**Important**:
- Provide specific, actionable feedback
- Use inline comments for line-specific issues
- Do NOT include a summary comment when submitting the review
- Submit as "COMMENT" type so the review doesn't block the PR
