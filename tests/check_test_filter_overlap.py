#!/usr/bin/env python3
"""Check that gtest filters in tests/ runner files don't overlap.

Each runner file under tests/ declares a ``test_context["filters"]`` list that
is shipped to the DUT as a gtest filter file. Two runners whose filters match
the same concrete gtest run that test twice, which skews pass rates. This
script scrapes the concrete TEST/TEST_F/... names out of the C++ sources for
each suite, replays the filters against them, and reports:

  duplicates          test currently claimed by more than one runner
  holes               test matched by some runner's includes but excluded
                      everywhere, so nothing runs it
  priority violations test owned by a lower-priority runner than the one that
                      should own it

Ownership priority within a suite is t0_* > t1_* > t2_* > everything else >
untiered; ties are broken by path.

Typed and parameterized tests are modelled under the names gtest actually
gives them -- ``AgentCoppTest/0.Foo``, ``Prefix/Suite.Foo/RECYCLE_PORT`` -- since
that is what the filters match. Naming that cannot be resolved statically, and
any runner file left owning no test at all, are hard failures: both would
otherwise make this check pass by looking at the wrong thing.

Runs standalone from a checkout, and as //fboss/tests:filter_overlap_test in
the Monobuild.
"""

from __future__ import annotations

import argparse
import ast
import fnmatch
import os
import pathlib
import re
import sys
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

GTEST_RE = re.compile(
    r"\b(TEST|TEST_F|TEST_P|TYPED_TEST|TYPED_TEST_P)\s*\(\s*"
    r"([A-Za-z_]\w*)\s*,\s*([A-Za-z_]\w*)\s*\)"
)
BENCH_RE = re.compile(r"\bBENCHMARK[A-Z_]*\s*\(\s*([A-Za-z_]\w*)")

# _CASE_ spellings are the pre-gtest-1.10 names; INSTANTIATE_TEST_CASE_P is
# still used in the tree.
TYPED_SUITE_RE = re.compile(
    r"\b(?:TYPED_TEST_SUITE|TYPED_TEST_CASE)\s*\(\s*([A-Za-z_]\w*)\s*,\s*([\w:]+)"
)
INSTANTIATE_TYPED_RE = re.compile(
    r"\b(?:INSTANTIATE_TYPED_TEST_SUITE_P|INSTANTIATE_TYPED_TEST_CASE_P)\s*\(\s*"
    r"([A-Za-z_]\w*)\s*,\s*([A-Za-z_]\w*)\s*,\s*([\w:]+)"
)
INSTANTIATE_P_RE = re.compile(
    r"\b(?:INSTANTIATE_TEST_SUITE_P|INSTANTIATE_TEST_CASE_P)\s*\("
)
TYPES_ALIAS_RE = re.compile(
    r"\busing\s+([A-Za-z_]\w*)\s*=\s*(?:::)?testing::\s*Types\s*<"
)
VALUES_RE = re.compile(r"(?:::)?testing::\s*Values\s*\(")
# Only name generator shape we can evaluate statically: the enum-name idiom.
ENUM_NAME_GEN_RE = re.compile(r"enumNameSafe\s*\(\s*\w+\s*\.\s*param\s*\)")
QUALIFIED_ENUM_RE = re.compile(r"^[\w:]*::([A-Za-z_]\w*)$")

CPP_EXTS = {".cpp", ".cc", ".cxx", ".h", ".hpp"}

UNTIERED_PRIORITY = 99


@dataclass(frozen=True)
class SuiteSpec:
    name: str
    fixture_names: Tuple[str, ...]
    source_dirs: Tuple[str, ...]
    path_filter: Optional[str] = None
    benchmark_mode: bool = False
    untiered_files: Tuple[str, ...] = ()
    supports_filters: bool = True


@dataclass
class RunnerFile:
    path: pathlib.Path
    relpath: str
    suite: str
    filters: List[str]
    includes: List[str]
    excludes: List[str]
    raw_matches: List[str]
    current_matches: List[str]
    priority: int


SUITES: Dict[str, SuiteSpec] = {
    "agent_hw": SuiteSpec(
        name="agent_hw",
        fixture_names=("sai_agent_test_runner",),
        source_dirs=("fboss/agent/test/agent_hw_tests",),
        untiered_files=("untiered_agent_hw_tests.py",),
    ),
    "qsfp": SuiteSpec(
        name="qsfp",
        fixture_names=("qsfp_test_runner",),
        source_dirs=("fboss/qsfp_service/test/hw_test",),
    ),
    "link": SuiteSpec(
        name="link",
        fixture_names=("link_test_runner",),
        source_dirs=("fboss/agent/test/link_tests",),
    ),
    "led": SuiteSpec(
        name="led",
        fixture_names=("led_service_hw_test_runner",),
        source_dirs=("fboss/led_service/hw_test",),
    ),
    "platform": SuiteSpec(
        name="platform",
        fixture_names=(
            "platform_hw_test_runner",
            "fan_service_hw_test_runner",
            "sensor_service_hw_test_runner",
            "fw_util_hw_test_runner",
            "weutil_hw_test_runner",
            "data_corral_service_hw_test_runner",
            "platform_manager_hw_test_runner",
        ),
        source_dirs=("fboss/platform",),
        # Matches both */hw_test/ and platform_hw_test/.
        path_filter="hw_test/",
    ),
    "bsp": SuiteSpec(
        name="bsp",
        fixture_names=("bsp_test_runner",),
        source_dirs=("fboss/platform/bsp_tests",),
        supports_filters=False,
    ),
}

FIXTURE_TO_SUITE = {
    fixture: suite_name
    for suite_name, spec in SUITES.items()
    for fixture in spec.fixture_names
}


def is_repo_root(candidate: pathlib.Path) -> bool:
    return (candidate / "tests" / "conftest.py").exists() and (
        candidate / "fboss" / "oss"
    ).is_dir()


def resolve_repo_root(explicit: Optional[str]) -> pathlib.Path:
    """Locate the FBOSS repo root, or under bazel the runfiles copy of it."""
    if explicit:
        candidate = pathlib.Path(explicit)
        if candidate.is_dir():
            return candidate
        # Bazel is expected to chdir into $TEST_SRCDIR/$TEST_WORKSPACE, but
        # don't depend on it: fall back to resolving against the runfiles root.
        srcdir = os.environ.get("TEST_SRCDIR")
        workspace = os.environ.get("TEST_WORKSPACE", "_main")
        if srcdir:
            from_runfiles = pathlib.Path(srcdir) / workspace / explicit
            if from_runfiles.is_dir():
                return from_runfiles
        raise SystemExit(f"--repo-root {explicit} does not exist (cwd={os.getcwd()})")

    here = pathlib.Path(__file__).resolve()
    for candidate in [here.parent] + list(here.parents):
        if is_repo_root(candidate):
            return candidate
    raise SystemExit("Could not infer FBOSS repo root from script location")


def split_filters(filters: List[str]) -> Tuple[List[str], List[str]]:
    includes: List[str] = []
    excludes: List[str] = []
    in_exclusions = False
    for item in filters:
        if item.startswith("-"):
            in_exclusions = True
            excludes.append(item[1:])
        elif in_exclusions:
            excludes.append(item)
        else:
            includes.append(item)
    return includes, excludes


def extract_filters_from_test_context(tree: ast.AST) -> Optional[List[str]]:
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id == "test_context":
                if not isinstance(node.value, ast.Dict):
                    continue
                for key, value in zip(node.value.keys, node.value.values):
                    if isinstance(key, ast.Constant) and key.value == "filters":
                        if not isinstance(value, ast.List):
                            return None
                        out: List[str] = []
                        for elt in value.elts:
                            if not isinstance(elt, ast.Constant) or not isinstance(
                                elt.value, str
                            ):
                                return None
                            out.append(elt.value)
                        return out
    return None


def extract_fixture_name(tree: ast.AST) -> Optional[str]:
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
            arg_names = [arg.arg for arg in node.args.args]
            for arg_name in arg_names:
                if arg_name in FIXTURE_TO_SUITE:
                    return arg_name
    return None


def parse_runner_file(pyfile: pathlib.Path) -> Optional[Tuple[str, List[str]]]:
    try:
        text = pyfile.read_text(encoding="utf-8")
    except OSError:
        return None
    try:
        tree = ast.parse(text, filename=str(pyfile))
    except SyntaxError:
        return None
    filters = extract_filters_from_test_context(tree)
    if not filters:
        return None
    fixture = extract_fixture_name(tree)
    if not fixture:
        return None
    return fixture, filters


def runner_priority(spec: SuiteSpec, filename: str) -> int:
    if filename in spec.untiered_files:
        return UNTIERED_PRIORITY
    if filename.startswith("t0_"):
        return 0
    if filename.startswith("t1_"):
        return 1
    if filename.startswith("t2_"):
        return 2
    return 3


def iter_source_files(repo: pathlib.Path, spec: SuiteSpec):
    for rel_dir in spec.source_dirs:
        base = repo / rel_dir
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if not path.is_file() or path.suffix not in CPP_EXTS:
                continue
            rel = path.relative_to(repo).as_posix()
            if spec.path_filter and spec.path_filter not in f"/{rel}/":
                continue
            yield path


_NESTING = {"(": ")", "[": "]", "{": "}", "<": ">"}


def match_block(text: str, open_idx: int, opener: str, closer: str) -> Optional[str]:
    """Contents of the balanced block whose opener sits at text[open_idx]."""
    depth = 0
    for idx in range(open_idx, len(text)):
        char = text[idx]
        if char == opener:
            depth += 1
        elif char == closer:
            depth -= 1
            if depth == 0:
                return text[open_idx + 1 : idx]
    return None


def split_top_level(inner: str) -> List[str]:
    """Split a macro or template argument list on its depth-0 commas."""
    parts: List[str] = []
    current: List[str] = []
    depth = 0
    for char in inner:
        if char in _NESTING:
            depth += 1
        elif char in _NESTING.values():
            depth -= 1
        if char == "," and depth == 0:
            parts.append("".join(current).strip())
            current = []
        else:
            current.append(char)
    tail = "".join(current).strip()
    if tail:
        parts.append(tail)
    return parts


@dataclass(frozen=True)
class SuiteNaming:
    """How gtest spells the concrete instances of one test suite."""

    kind: str  # "typed" or "param"
    suffixes: Tuple[str, ...]
    prefix: str = ""


def types_alias_arity(text: str) -> Dict[str, int]:
    """Map ``using X = testing::Types<...>`` aliases to their type count."""
    arity: Dict[str, int] = {}
    for match in TYPES_ALIAS_RE.finditer(text):
        inner = match_block(text, match.end() - 1, "<", ">")
        if inner is not None:
            arity[match.group(1)] = len(split_top_level(inner))
    return arity


def param_values(args: List[str]) -> Tuple[List[str], str]:
    """Values an INSTANTIATE_*_P generator expands to, or ([], why-not)."""
    if len(args) < 3:
        return [], "malformed INSTANTIATE, fewer than 3 arguments"
    generator = args[2]
    match = VALUES_RE.match(generator)
    if not match:
        head = generator.split("(")[0].strip() or generator
        return [], f"unsupported value generator {head}"
    inner = match_block(generator, match.end() - 1, "(", ")")
    if inner is None:
        return [], "unbalanced value generator arguments"
    values = split_top_level(inner)
    if not values:
        return [], "empty value generator"
    return values, ""


def param_suffixes(args: List[str]) -> Tuple[Optional[Tuple[str, ...]], str]:
    """Suffixes gtest appends per value of an INSTANTIATE_*_P, or (None, why)."""
    values, reason = param_values(args)
    if not values:
        return None, reason
    if len(args) == 3:
        # No name generator, so gtest suffixes with the value's index.
        return tuple(str(idx) for idx in range(len(values))), ""
    if not ENUM_NAME_GEN_RE.search(args[3]):
        return None, "name generator is not the enumNameSafe(info.param) idiom"
    names: List[str] = []
    for value in values:
        enum_match = QUALIFIED_ENUM_RE.match(value)
        if not enum_match:
            return None, f"name generator input {value} is not an enum literal"
        names.append(enum_match.group(1))
    return tuple(names), ""


def collect_suite_naming(
    texts: Dict[str, str],
) -> Tuple[Dict[str, SuiteNaming], Dict[str, str]]:
    """Resolve instantiation naming per suite; returns (naming, why-not).

    Type aliases are file-local by convention -- several files declare their
    own ``TestTypes`` -- so resolve inside the declaring file first and only
    fall back to a repo-wide alias when its arity is unambiguous.
    """
    alias_by_file = {rel: types_alias_arity(text) for rel, text in texts.items()}
    global_alias: Dict[str, set] = {}
    for aliases in alias_by_file.values():
        for alias, count in aliases.items():
            global_alias.setdefault(alias, set()).add(count)

    def arity(rel: str, alias: str) -> Tuple[Optional[int], str]:
        local = alias_by_file[rel].get(alias)
        if local is not None:
            return local, ""
        counts = global_alias.get(alias)
        if not counts:
            return None, f"type list {alias} not found"
        if len(counts) > 1:
            return None, f"type list {alias} has ambiguous arity {sorted(counts)}"
        return next(iter(counts)), ""

    naming: Dict[str, SuiteNaming] = {}
    unresolved: Dict[str, str] = {}
    for rel, text in texts.items():
        for match in TYPED_SUITE_RE.finditer(text):
            suite, alias = match.group(1), match.group(2)
            count, reason = arity(rel, alias)
            if count is None:
                unresolved[suite] = reason
                continue
            naming[suite] = SuiteNaming(
                "typed", tuple(str(idx) for idx in range(count))
            )
        for match in INSTANTIATE_TYPED_RE.finditer(text):
            prefix, suite, alias = match.group(1), match.group(2), match.group(3)
            count, reason = arity(rel, alias)
            if count is None:
                unresolved[suite] = reason
                continue
            naming[suite] = SuiteNaming(
                "typed", tuple(str(idx) for idx in range(count)), prefix
            )
        for match in INSTANTIATE_P_RE.finditer(text):
            inner = match_block(text, match.end() - 1, "(", ")")
            if inner is None:
                continue
            args = split_top_level(inner)
            if len(args) < 2:
                continue
            suite = args[1]
            suffixes, reason = param_suffixes(args)
            if suffixes is None:
                unresolved[suite] = reason
                continue
            naming[suite] = SuiteNaming("param", suffixes, args[0])
    return naming, unresolved


def instance_names(suite: str, test: str, spelling: SuiteNaming) -> List[str]:
    if spelling.kind == "typed":
        prefix = f"{spelling.prefix}/" if spelling.prefix else ""
        return [f"{prefix}{suite}/{sfx}.{test}" for sfx in spelling.suffixes]
    return [f"{spelling.prefix}/{suite}.{test}/{sfx}" for sfx in spelling.suffixes]


def scrape_concrete_tests(
    repo: pathlib.Path, spec: SuiteSpec
) -> Tuple[List[str], List[str]]:
    """Concrete gtest names for a suite, plus unresolvable-naming complaints.

    Typed and parameterized tests are not named ``Suite.Test`` at run time:
    gtest appends the instantiation to the suite (``AgentCoppTest/0.Foo``) or
    the value to the test (``Prefix/Suite.Foo/RECYCLE_PORT``). Runner filters
    are written against those real names, so model them rather than the macro
    spelling -- otherwise a filter like ``*AgentCoppTest/0*`` silently matches
    nothing and the runner looks like it owns no tests.
    """
    texts: Dict[str, str] = {}
    for path in iter_source_files(repo, spec):
        try:
            texts[path.relative_to(repo).as_posix()] = path.read_text(
                encoding="utf-8", errors="ignore"
            )
        except OSError:
            continue

    names = set()
    if spec.benchmark_mode:
        for text in texts.values():
            for match in BENCH_RE.finditer(text):
                names.add(match.group(1))
        return sorted(names), []

    naming, unresolved = collect_suite_naming(texts)
    unnamed: Dict[str, str] = {}
    for text in texts.values():
        for match in GTEST_RE.finditer(text):
            macro, suite, test = match.group(1), match.group(2), match.group(3)
            if macro in ("TEST", "TEST_F"):
                names.add(f"{suite}.{test}")
                continue
            spelling = naming.get(suite)
            if spelling is None:
                unnamed[suite] = unresolved.get(
                    suite, f"no instantiation found for {macro} suite"
                )
                continue
            names.update(instance_names(suite, test, spelling))
    complaints = [
        f"suite={spec.name}: cannot determine instantiated names for {suite} ({reason})"
        for suite, reason in sorted(unnamed.items())
    ]
    return sorted(names), complaints


def match_any(test_name: str, patterns: List[str]) -> bool:
    return any(fnmatch.fnmatchcase(test_name, pat) for pat in patterns)


def apply_filters(
    includes: List[str], excludes: List[str], tests: List[str]
) -> Tuple[List[str], List[str]]:
    raw = [t for t in tests if match_any(t, includes)]
    current = [t for t in raw if not match_any(t, excludes)]
    return raw, current


def collect_runners(
    repo: pathlib.Path, suite_tests: Dict[str, List[str]]
) -> Tuple[Dict[str, List[RunnerFile]], List[str]]:
    by_suite: Dict[str, List[RunnerFile]] = {name: [] for name in SUITES}
    skipped: List[str] = []
    for pyfile in sorted((repo / "tests").rglob("*.py")):
        if pyfile.name in {"__init__.py", "conftest.py"}:
            continue
        parsed = parse_runner_file(pyfile)
        if not parsed:
            continue
        fixture, filters = parsed
        suite_name = FIXTURE_TO_SUITE[fixture]
        spec = SUITES[suite_name]
        if not spec.supports_filters:
            skipped.append(
                f"{pyfile.relative_to(repo)} "
                f"(suite={suite_name}: runner ignores filter files)"
            )
            continue
        includes, excludes = split_filters(filters)
        raw, current = apply_filters(includes, excludes, suite_tests[suite_name])
        by_suite[suite_name].append(
            RunnerFile(
                path=pyfile,
                relpath=pyfile.relative_to(repo).as_posix(),
                suite=suite_name,
                filters=filters,
                includes=includes,
                excludes=excludes,
                raw_matches=raw,
                current_matches=current,
                priority=runner_priority(spec, pyfile.name),
            )
        )
    return by_suite, skipped


def classify_suite(
    spec: SuiteSpec, runners: List[RunnerFile], tests: List[str]
) -> dict:
    tiered = [r for r in runners if r.priority != UNTIERED_PRIORITY]
    untiered = [r for r in runners if r.priority == UNTIERED_PRIORITY]

    duplicates = {}
    holes = {}
    priority_violations = {}

    for test in tests:
        raw_candidates = sorted(
            [r for r in tiered if test in r.raw_matches],
            key=lambda r: (r.priority, r.relpath),
        )
        current_owners = sorted(
            [r for r in tiered if test in r.current_matches],
            key=lambda r: (r.priority, r.relpath),
        )
        expected_owner = (
            raw_candidates[0].relpath
            if raw_candidates
            else (untiered[0].relpath if untiered else None)
        )
        current_owner_paths = [r.relpath for r in current_owners]
        raw_candidate_paths = [r.relpath for r in raw_candidates]

        if len(current_owner_paths) > 1:
            duplicates[test] = {
                "expected_owner": expected_owner,
                "current_owners": current_owner_paths,
            }
        if raw_candidate_paths and not current_owner_paths:
            holes[test] = {
                "expected_owner": expected_owner,
                "raw_candidates": raw_candidate_paths,
            }
        if (
            raw_candidate_paths
            and current_owner_paths
            and current_owner_paths[0] != expected_owner
        ):
            priority_violations[test] = {
                "expected_owner": expected_owner,
                "current_owners": current_owner_paths,
            }

    return {
        "duplicates": duplicates,
        "holes": holes,
        "priority_violations": priority_violations,
    }


def print_suite_report(spec: SuiteSpec, result: dict) -> int:
    failures = 0
    duplicates = result["duplicates"]
    holes = result["holes"]
    priority_violations = result["priority_violations"]

    if not duplicates and not holes and not priority_violations:
        return 0

    print(f"== Suite: {spec.name} ==")
    if duplicates:
        failures += len(duplicates)
        print("Duplicate current owners:")
        for test, info in sorted(duplicates.items()):
            print(f"  {test}")
            print(f"    expected_owner: {info['expected_owner']}")
            print(f"    current_owners: {', '.join(info['current_owners'])}")
    if holes:
        failures += len(holes)
        print("Tests with raw matches but zero current owners:")
        for test, info in sorted(holes.items()):
            print(f"  {test}")
            print(f"    expected_owner: {info['expected_owner']}")
            print(f"    raw_candidates: {', '.join(info['raw_candidates'])}")
    if priority_violations:
        failures += len(priority_violations)
        print("Priority violations:")
        for test, info in sorted(priority_violations.items()):
            print(f"  {test}")
            print(f"    expected_owner: {info['expected_owner']}")
            print(f"    current_owners: {', '.join(info['current_owners'])}")
    print()
    return failures


def check_inputs_present(
    repo: pathlib.Path,
    by_suite: Dict[str, List[RunnerFile]],
    suite_tests: Dict[str, List[str]],
) -> List[str]:
    """Guard against silently checking nothing.

    Under bazel the inputs are whatever the BUILD file declared as data. A
    missing source dir or runner file would otherwise turn this into a test
    that passes because it looked at an empty tree.
    """
    problems: List[str] = []
    for suite_name, spec in SUITES.items():
        if not spec.supports_filters:
            continue
        for rel_dir in spec.source_dirs:
            if not (repo / rel_dir).is_dir():
                problems.append(f"suite={suite_name}: missing source dir {rel_dir}")
        if not suite_tests.get(suite_name):
            problems.append(f"suite={suite_name}: scraped 0 gtest names")
        if not by_suite.get(suite_name):
            problems.append(f"suite={suite_name}: found 0 runner files under tests/")
        for runner in by_suite.get(suite_name, []):
            if not runner.raw_matches:
                problems.append(
                    f"suite={suite_name}: {runner.relpath} matches no known test "
                    f"(includes: {', '.join(runner.includes)})"
                )
            elif not runner.current_matches:
                problems.append(
                    f"suite={suite_name}: {runner.relpath} excludes every test it "
                    "includes, so it runs nothing"
                )
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo-root",
        help=(
            "FBOSS repo root to inspect. Defaults to auto-detection from this "
            "script's location; bazel passes the runfiles path explicitly."
        ),
    )
    args = parser.parse_args()

    repo = resolve_repo_root(args.repo_root)

    scraped = {
        name: scrape_concrete_tests(repo, spec)
        for name, spec in SUITES.items()
        if spec.supports_filters
    }
    suite_tests = {name: names for name, (names, _) in scraped.items()}
    naming_problems = [
        complaint for _, complaints in scraped.values() for complaint in complaints
    ]

    by_suite, skipped = collect_runners(repo, suite_tests)

    problems = naming_problems + check_inputs_present(repo, by_suite, suite_tests)
    if problems:
        print(f"Input and naming problems under {repo}:")
        for problem in problems:
            print(f"  {problem}")
        print()

    total_failures = len(problems)
    for suite_name, spec in SUITES.items():
        if not spec.supports_filters:
            continue
        tests = suite_tests[suite_name]
        runners = by_suite[suite_name]
        if not runners or not tests:
            continue
        result = classify_suite(spec, runners, tests)
        total_failures += print_suite_report(spec, result)

    if skipped:
        print("Skipped suites/files:")
        for item in skipped:
            print(f"  {item}")
        print()

    if total_failures:
        print(f"FAIL: found {total_failures} overlap/ownership issue(s)")
        return 1
    print("PASS: no overlap or ownership issues found")
    return 0


if __name__ == "__main__":
    sys.exit(main())
