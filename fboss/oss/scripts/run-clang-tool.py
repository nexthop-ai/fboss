#!/usr/bin/env python3
"""
Parallel clang tool runner.

Runs a clang tool (clang-tidy, clang-include-cleaner, etc.) in parallel on a
set of C++ files, with concurrency capped by both CPU count and available RAM
(assuming 6 GB per worker).

Usage:
    run-clang-tool.py [--tool TOOL] [--build-dir DIR] \
        [--dirty | --head | file1.cpp file2.h ...] \
        [-- extra-tool-args ...]
"""

import argparse
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

DEFAULT_BUILD_DIR = "/var/FBOSS/tmp_bld_dir/build/fboss"
RAM_PER_WORKER_GB = 6  # Clang tools use a lot of RAM.
CPP_EXTENSIONS = {".cpp", ".h"}  # Nothing else is used in FBOSS
REPO_ROOT = Path(__file__).resolve().parents[3]


def set_oom_score() -> None:
    try:
        with open("/proc/self/oom_score_adj", "w") as f:
            f.write("1000\n")
    except OSError:
        pass  # Non-Linux or no permission — continue anyway


def compute_jobs() -> int:
    try:
        ram_bytes = os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES")
        ram_gb = ram_bytes / (1024**3)
        ram_jobs = max(1, int(ram_gb // RAM_PER_WORKER_GB))
    except (ValueError, OSError):
        ram_jobs = 1
    cpu_jobs = os.cpu_count() or 1
    return min(ram_jobs, cpu_jobs)


def filter_cpp_files(paths: list[str]) -> list[str]:
    # .exists() filters out files deleted in the diff (they appear in git output
    # but are gone from the working tree). Added/modified files exist on HEAD and
    # are correctly included.
    return [p for p in paths if Path(p).suffix in CPP_EXTENSIONS and Path(p).exists()]


def get_dirty_files() -> list[str]:
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        capture_output=True,
        text=True,
        check=True,
    )
    paths = []
    for line in result.stdout.splitlines():
        if len(line) < 4:
            continue
        path = line[3:].strip()
        # Handle renamed files (old -> new)
        if " -> " in path:
            path = path.split(" -> ")[-1]
        paths.append(path)
    return filter_cpp_files(paths)


def get_head_files() -> list[str]:
    result = subprocess.run(
        ["git", "show", "--name-only", "--format=", "HEAD"],
        capture_output=True,
        text=True,
        check=True,
    )
    paths = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    return filter_cpp_files(paths)


def get_range_files(range_spec: str) -> list[str]:
    result = subprocess.run(
        [
            "git",
            "diff",
            "--name-only",
            range_spec,
            "--",
            *[f"*{ext}" for ext in CPP_EXTENSIONS],
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    paths = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    return filter_cpp_files(paths)


def terminal_width() -> int:
    try:
        return os.get_terminal_size().columns
    except OSError:
        return 80


def make_progress_bar(done: int, total: int) -> str:
    term_width = terminal_width()
    suffix = f" {done}/{total}"
    # brackets + suffix leave the rest for the bar fill
    bar_width = max(1, term_width - 2 - len(suffix))
    filled = int(bar_width * done / total) if total else 0
    arrow = ">" if filled < bar_width else ""
    bar = ("=" * filled + arrow).ljust(bar_width)
    return f"[{bar}]{suffix}"


def run_on_file(
    tool: str, build_dir: str, extra_args: list[str], filepath: str
) -> tuple[str, int, str]:
    cmd = [tool, "-p", build_dir, *extra_args, filepath]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    return filepath, result.returncode, result.stdout + result.stderr


def refresh_compile_commands_if_stale(compile_commands: Path, files: list[str]) -> None:
    """If we have a Bazel build (MODULE.bazel present) and compile_commands.json
    is missing or older than any input file, regenerate it via Hedron."""
    if not (REPO_ROOT / "MODULE.bazel").exists():
        return  # No Bazel build configured — leave compile_commands.json alone

    if compile_commands.exists():
        cc_mtime = compile_commands.stat().st_mtime
        newest_input = max(
            (Path(f).stat().st_mtime for f in files if Path(f).exists()),
            default=0,
        )
        if newest_input <= cc_mtime:
            return  # Up to date

    print(
        "compile_commands.json is stale or missing — regenerating via Bazel...",
        file=sys.stderr,
    )
    # Capture the extractor's output. On success it can be thousands of
    # lines of Bazel action-graph dump that would flood the terminal; on
    # failure we print it so the user can diagnose.
    result = subprocess.run(
        [
            str(REPO_ROOT / "fboss" / "oss" / "scripts" / "bazel.sh"),
            "run",
            "//fboss/build_defs:refresh_compile_commands",
        ],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        sys.stderr.write(result.stdout)
        sys.stderr.write(result.stderr)
        print(
            "WARNING: refresh_compile_commands failed; using existing "
            "compile_commands.json if present",
            file=sys.stderr,
        )


def collect_files(args: argparse.Namespace) -> list[str]:
    if args.dirty:
        return get_dirty_files()
    if args.head:
        return get_head_files()
    if args.range:
        return get_range_files(args.range)
    return list(args.files)


def run_parallel(
    tool: str, build_dir: str, extra_args: list[str], files: list[str], jobs: int
) -> list[tuple[str, int]]:
    is_tty = sys.stdout.isatty()
    total = len(files)
    done_count = 0
    failed = []

    with ThreadPoolExecutor(max_workers=jobs) as executor:
        futures = {
            executor.submit(run_on_file, tool, build_dir, extra_args, f): f
            for f in files
        }

        if is_tty:
            print(
                f"\r{make_progress_bar(0, total)}", end="", flush=True, file=sys.stderr
            )

        for future in as_completed(futures):
            filepath, returncode, output = future.result()
            done_count += 1
            if is_tty:
                # Clear bar, print output, redraw bar so diagnostics appear above it
                term_width = terminal_width()
                prefix = f"\r{' ' * term_width}\r"
                bar = f"\r{make_progress_bar(done_count, total)}"
                sys.stderr.write(prefix + output + bar)
                sys.stderr.flush()
            else:
                sys.stdout.write(output)
                sys.stdout.flush()
            if returncode != 0:
                failed.append((filepath, returncode))

    if is_tty:
        term_width = os.get_terminal_size().columns
        print(f"\r{' ' * term_width}\r", end="", flush=True, file=sys.stderr)

    return failed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run a clang tool in parallel on C++ files."
    )
    tool_group = parser.add_mutually_exclusive_group()
    tool_group.add_argument(
        "--tool",
        default=None,
        help="Clang tool to run (default: clang-tidy)",
    )
    tool_group.add_argument(
        "--include-cleaner",
        action="store_true",
        help="Shorthand for --tool=clang-include-cleaner -- --edit",
    )
    parser.add_argument(
        "--build-dir",
        default=DEFAULT_BUILD_DIR,
        metavar="DIR",
        help=f"Build directory with compile_commands.json (default: {DEFAULT_BUILD_DIR})",
    )
    source_group = parser.add_mutually_exclusive_group()
    source_group.add_argument(
        "--dirty",
        action="store_true",
        help="Run on files modified in the working tree (git status)",
    )
    source_group.add_argument(
        "--head",
        action="store_true",
        help="Run on files changed in the HEAD commit",
    )
    source_group.add_argument(
        "--range",
        metavar="RANGE",
        help="Run on files changed in a git range, e.g. --range abc123..HEAD",
    )
    parser.add_argument(
        "files",
        nargs="*",
        metavar="FILE",
        help="Explicit list of files to process",
    )
    parser.add_argument(
        "--no-run-if-empty",
        action="store_true",
        help="Exit 0 silently if there are no files to process (like xargs --no-run-if-empty)",
    )
    return parser


def main() -> None:
    # Split args at '--' to separate tool pass-through args
    argv = sys.argv[1:]
    try:
        sep = argv.index("--")
        our_argv, extra_args = argv[:sep], argv[sep + 1 :]
    except ValueError:
        our_argv, extra_args = argv, []

    parser = build_parser()
    args = parser.parse_args(our_argv)

    if (args.dirty or args.head or args.range) and args.files:
        parser.error(
            "Cannot combine --dirty/--head/--range with explicit file arguments"
        )

    if args.include_cleaner:
        tool = "clang-include-cleaner"
        extra_args = ["--edit", *extra_args]
    else:
        tool = args.tool or "clang-tidy"

    # OOM protection — do this before anything else
    set_oom_score()

    files = collect_files(args)
    if not files:
        print("No files to process.", file=sys.stderr)
        sys.exit(0 if args.no_run_if_empty else 1)

    compile_commands = Path(args.build_dir) / "compile_commands.json"
    refresh_compile_commands_if_stale(compile_commands, files)
    if not compile_commands.exists():
        print(
            f"ERROR: compile_commands.json not found in {args.build_dir}",
            file=sys.stderr,
        )
        sys.exit(1)

    jobs = min(compute_jobs(), len(files))
    print(
        f"Running {tool} on {len(files)} file(s) with {jobs} worker(s) "
        f"(build-dir: {args.build_dir})",
        file=sys.stderr,
    )

    failed = run_parallel(tool, args.build_dir, extra_args, files, jobs)

    if failed:
        print(f"{len(failed)} file(s) failed:", file=sys.stderr)
        for f, rc in failed:
            print(f"  {f} (exit {rc})", file=sys.stderr)
        sys.exit(1)

    print("All files processed successfully.", file=sys.stderr)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
