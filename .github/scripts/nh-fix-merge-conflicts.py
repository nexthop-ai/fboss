#!/usr/bin/env python3
"""
Automatically fix merge conflicts in CMake and BUCK files where conflicts are only in file lists.

This script is designed to handle merge conflicts that occur when syncing changes from
upstream, where both sides of the conflict contain only file paths in file lists.

The script:
1. Finds all .cmake files in cmake/ and BUCK files throughout the repo with merge conflicts
2. For each conflict, checks if all conflicting lines are file paths
3. Takes the union of file paths from both sides of the conflict
4. Removes any files that don't exist in the working directory
5. Sorts the files alphabetically
6. Replaces the conflict with the resolved list

Usage:
    .github/scripts/nh-fix-merge-conflicts.py

The script will:
- Process all .cmake files in the cmake/ directory
- Process all BUCK files in the repository
- Only fix conflicts where all lines are file paths
- Leave other conflicts untouched for manual resolution
- Report which conflicts were resolved and which were skipped

Example CMake conflict that will be auto-resolved:
    <<<<<<< HEAD
    fboss/cli/fboss2/commands/foo/Foo.cpp
    fboss/cli/fboss2/commands/foo/Foo.h
    fboss/cli/fboss2/commands/bar/Bar.cpp
    ||||||| base
    =======
    fboss/cli/fboss2/commands/foo/Foo.h
    fboss/cli/fboss2/commands/baz/Baz.cpp
    >>>>>>> upstream

Example BUCK conflict that will be auto-resolved:
    <<<<<<< HEAD
        "commands/foo/Foo.cpp",
        "commands/foo/Foo.h",
        "commands/bar/Bar.cpp",
    ||||||| base
    =======
        "commands/foo/Foo.h",
        "commands/baz/Baz.cpp",
    >>>>>>> upstream

Both will be resolved to (union, sorted, only existing files).
"""

from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional
from enum import Enum
import subprocess


class FileFormat(Enum):
    """File format types for different build systems."""
    CMAKE = "cmake"
    BUCK = "buck"
    CPP_INCLUDE = "cpp_include"


def strip_buck_inline_comment(stripped: str) -> str:
    """Strip a trailing inline comment from a BUCK file path line.

    Handles lines like '"path/to/file.cpp",  # bazelify: exclude'
    by returning '"path/to/file.cpp",' with the comment removed.
    """
    if '#' not in stripped:
        return stripped
    hash_idx = stripped.rfind('#')
    before_hash = stripped[:hash_idx].rstrip()
    # Only strip if what remains still looks like a quoted path entry
    if before_hash.endswith('",') or before_hash.endswith('"'):
        return before_hash
    return stripped


def extract_buck_path_annotations(lines: List[str]) -> Dict[str, str]:
    """Return a mapping of file path -> inline annotation for BUCK file lines.

    For example, '"utils/NetwhoamiUtils.cpp",  # bazelify: exclude' yields
    {'utils/NetwhoamiUtils.cpp': '  # bazelify: exclude'}.
    """
    annotations: Dict[str, str] = {}
    for line in lines:
        stripped = line.strip()
        if not stripped.startswith('"') or '#' not in stripped:
            continue
        without_comment = strip_buck_inline_comment(stripped)
        if without_comment == stripped:
            continue  # no comment was stripped
        path = without_comment.strip('",').strip('"')
        hash_idx = stripped.rfind('#')
        annotations[path] = '  ' + stripped[hash_idx:]
    return annotations


def is_file_path_line(line: str, file_format: FileFormat) -> bool:
    """Check if a line looks like a file path in a file list."""
    stripped = line.strip()
    # Empty lines are OK in file lists
    if not stripped:
        return True

    if file_format == FileFormat.CMAKE:
        # Should not contain CMake commands or other syntax
        if any(keyword in stripped for keyword in ['(', ')', 'add_', 'target_', 'set(', 'if(', 'endif(', 'else(', 'elseif(']):
            return False
        # Should look like a path (contains forward slashes or is a simple filename)
        return '/' in stripped or stripped.endswith(('.cpp', '.h', '.c'))

    elif file_format == FileFormat.CPP_INCLUDE:
        # C++ include statements
        # Should be #include "..." or #include <...>
        if not stripped.startswith('#include'):
            return False
        # Extract the included file
        if '"' in stripped:
            # #include "path/to/file.h"
            return True
        # Angle-bracket includes (#include <...>) can't be existence-checked
        # against the repo, so skip those conflicts for manual resolution
        return False

    elif file_format == FileFormat.BUCK:
        # BUCK files use quoted strings with commas
        # Should not contain BUCK keywords or other syntax (except quotes and commas)
        if any(keyword in stripped for keyword in ['load(', 'name =', 'srcs =', 'headers =', 'deps =', 'visibility =', 'cpp_library(', 'cpp_binary(']):
            return False
        # Strip inline annotations (e.g. # bazelify: exclude) before checking
        stripped = strip_buck_inline_comment(stripped)
        # Should be a quoted string, possibly with a trailing comma
        if stripped.startswith('"') and (stripped.endswith('",') or stripped.endswith('"')):
            # Extract the path from quotes
            path = stripped.strip('",').strip('"')
            # BUCK targets (starting with //) cannot be validated by this script
            # Return False so conflicts containing them are skipped for manual resolution
            if path.startswith('//'):
                return False
            # File paths should contain / or end with source extensions
            return '/' in path or path.endswith(('.cpp', '.h', '.c'))
        return False

    return False


def extract_file_paths(lines: List[str], file_format: FileFormat) -> Set[str]:
    """Extract file paths from a list of lines, ignoring empty lines."""
    paths = set()
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        if file_format == FileFormat.BUCK:
            # Extract path from quoted string, removing quotes, trailing comma, and inline comment
            if stripped.startswith('"'):
                path = strip_buck_inline_comment(stripped).strip('",').strip('"')
                paths.add(path)
        elif file_format == FileFormat.CPP_INCLUDE:
            # Extract path from #include "..." or #include <...>
            if stripped.startswith('#include'):
                # Remove #include prefix
                rest = stripped[8:].strip()
                # Extract the path from quotes or angle brackets
                if rest.startswith('"') and '"' in rest[1:]:
                    path = rest[1:rest.index('"', 1)]
                    paths.add(path)
                elif rest.startswith('<') and '>' in rest[1:]:
                    path = rest[1:rest.index('>', 1)]
                    paths.add(path)
        else:
            # CMake format - just use the stripped line (skip comments)
            if not stripped.startswith('#'):
                paths.add(stripped)
    return paths


def file_exists(filepath: str, repo_root: Path, base_dir: Path) -> bool:
    """Check if a file exists in the repository."""
    # Try relative to base_dir first (for BUCK files)
    full_path = base_dir / filepath
    if full_path.exists() and full_path.is_file():
        return True
    # Try relative to repo_root (for CMake files)
    full_path = repo_root / filepath
    return full_path.exists() and full_path.is_file()


def parse_conflict_block(lines: List[str], start_idx: int) -> Optional[Tuple[int, List[str], List[str], int]]:
    """
    Parse a conflict block starting at start_idx.

    Returns: (start_idx, ours_lines, theirs_lines, end_idx) or None if not a valid conflict
    """
    if not lines[start_idx].startswith('<<<<<<< HEAD'):
        return None

    # Find the markers
    ours_start = start_idx + 1
    base_marker = None
    theirs_start = None
    end_marker = None

    for i in range(start_idx + 1, len(lines)):
        if lines[i].startswith('|||||||'):
            base_marker = i
        elif lines[i].startswith('======='):
            theirs_start = i + 1
        elif lines[i].startswith('>>>>>>>'):
            end_marker = i
            break

    if theirs_start is None or end_marker is None:
        return None

    # Extract the lines from each side
    if base_marker is not None:
        ours_end = base_marker
    else:
        ours_end = theirs_start - 1

    ours_lines = lines[ours_start:ours_end]
    theirs_lines = lines[theirs_start:end_marker]

    return (start_idx, ours_lines, theirs_lines, end_marker)


def collect_context_paths(above_lines: List[str], below_lines: List[str], below_start: int, file_format: FileFormat) -> Set[str]:
    """
    Collect file paths from the contiguous path-line runs surrounding a
    conflict: walking backwards through already-emitted lines and forwards
    through the remaining input. The walks stop at the first non-path line
    (a list boundary), so the result never crosses into a neighboring
    target's list. Sibling conflict blocks are stepped over without counting
    their contents (they get their own resolution pass) — unless the block
    itself contains a structural line, in which case it straddles a list
    boundary and the walk stops there too.
    """
    def _is_marker(line: str) -> bool:
        return line.startswith(('<<<<<<<', '|||||||', '=======', '>>>>>>>'))

    def _block_is_all_paths(lines: List[str], start: int, end: int) -> bool:
        """True if every non-marker line in lines[start:end+1] is a path line."""
        return all(
            _is_marker(lines[k]) or is_file_path_line(lines[k], file_format)
            for k in range(start, end + 1)
        )

    context: Set[str] = set()
    j = len(above_lines) - 1
    while j >= 0:
        if above_lines[j].startswith('>>>>>>>'):
            # Step over a sibling conflict block without counting its contents
            # as context; it gets its own resolution pass. If the block holds
            # any structural (non-path) line, it straddles a list boundary —
            # stop rather than leak the neighboring list into the context.
            k = j
            while k >= 0 and not above_lines[k].startswith('<<<<<<<'):
                k -= 1
            if k < 0 or not _block_is_all_paths(above_lines, k, j):
                break
            j = k - 1
            continue
        if not is_file_path_line(above_lines[j], file_format):
            break
        context |= extract_file_paths([above_lines[j]], file_format)
        j -= 1
    j = below_start
    while j < len(below_lines):
        if below_lines[j].startswith('<<<<<<<'):
            k = j
            while k < len(below_lines) and not below_lines[k].startswith('>>>>>>>'):
                k += 1
            if k >= len(below_lines) or not _block_is_all_paths(below_lines, j, k):
                break
            j = k + 1
            continue
        if not is_file_path_line(below_lines[j], file_format):
            break
        context |= extract_file_paths([below_lines[j]], file_format)
        j += 1
    return context


def resolve_conflict(ours_lines: List[str], theirs_lines: List[str], repo_root: Path, base_dir: Path, file_format: FileFormat, context_paths: Optional[Set[str]] = None) -> Optional[List[str]]:
    """
    Resolve a conflict by taking the union of file paths.

    Paths in context_paths (entries already present elsewhere in the enclosing
    list) are dropped from the union: when internal and upstream carry the same
    entries at different positions, git emits paired one-sided conflict hunks,
    and a per-hunk union would keep both copies. CMake/Buck silently dedup
    sources, so such duplicates survive builds unnoticed.

    Returns the resolved lines, or None if the conflict can't be auto-resolved.
    """
    # Check if all lines are file paths
    for line in ours_lines + theirs_lines:
        if not is_file_path_line(line, file_format):
            return None

    # Extract file paths from both sides
    ours_paths = extract_file_paths(ours_lines, file_format)
    theirs_paths = extract_file_paths(theirs_lines, file_format)

    # For BUCK files, collect inline annotations (e.g. # bazelify: exclude) from our side
    # so they can be preserved in the output.
    ours_annotations: Dict[str, str] = {}
    if file_format == FileFormat.BUCK:
        ours_annotations = extract_buck_path_annotations(ours_lines)

    # Take the union, minus entries the enclosing list already has
    all_paths = ours_paths | theirs_paths
    if context_paths:
        all_paths -= context_paths

    # Filter out non-existent files
    existing_paths = {path for path in all_paths if file_exists(path, repo_root, base_dir)}

    # Sort alphabetically
    sorted_paths = sorted(existing_paths)

    # Format based on file type
    if file_format == FileFormat.CMAKE:
        # CMake format: 2-space indentation
        resolved_lines = [f"  {path}\n" for path in sorted_paths]
    elif file_format == FileFormat.CPP_INCLUDE:
        # C++ include format: #include "path"
        resolved_lines = [f'#include "{path}"\n' for path in sorted_paths]
    else:  # BUCK format
        # BUCK format: 8-space indentation, quoted strings with trailing commas
        # Preserve any inline annotations (e.g. # bazelify: exclude) from our side
        resolved_lines = [f'        "{path}",{ours_annotations.get(path, "")}\n' for path in sorted_paths]

    return resolved_lines


def show_git_diff(file_path: Path, original_content: str) -> None:
    """Show the diff between original conflicted content and resolved content."""
    try:
        # Create a simple diff output
        print(f"\n  Changes made to {file_path}:")

        # Use git diff with stdin to show clearly what we changed
        result = subprocess.run(
            ['git', 'diff', '--no-index', '--color=never', '/dev/stdin', str(file_path)],
            input=original_content,
            capture_output=True,
            text=True,
            check=False
        )

        if result.stdout:
            # Skip the first 4 lines (diff header, index, ---, +++)
            lines = result.stdout.splitlines()[4:]
            print("  " + "\n  ".join(lines))
            print()
    except Exception as e:
        print(f"  Warning: Could not show diff for {file_path}: {e}")


def process_file(filepath: Path, repo_root: Path, file_format: FileFormat) -> bool:
    """
    Process a single file and fix auto-resolvable conflicts.

    Returns True if any changes were made.
    """
    # For BUCK files, paths are relative to the BUCK file's directory
    # For CMake files, paths are relative to the repo root
    base_dir = filepath.parent if file_format == FileFormat.BUCK else repo_root

    with open(filepath, 'r') as f:
        lines = f.readlines()

    # Save original content for diff display
    original_content = ''.join(lines)

    modified = False
    has_unresolved_conflicts = False
    i = 0
    new_lines = []

    while i < len(lines):
        if lines[i].startswith('<<<<<<< HEAD'):
            result = parse_conflict_block(lines, i)
            if result:
                start_idx, ours_lines, theirs_lines, end_idx = result
                context_paths = collect_context_paths(new_lines, lines, end_idx + 1, file_format)
                resolved = resolve_conflict(ours_lines, theirs_lines, repo_root, base_dir, file_format, context_paths)

                if resolved is not None:
                    # Replace the conflict with the resolved version
                    new_lines.extend(resolved)
                    i = end_idx + 1
                    modified = True
                    print(f"  ✓ Resolved conflict at line {start_idx + 1}")
                else:
                    # Can't auto-resolve, keep the conflict as-is
                    new_lines.extend(lines[start_idx:end_idx + 1])
                    i = end_idx + 1
                    has_unresolved_conflicts = True
                    print(f"  ✗ Skipped conflict at line {start_idx + 1} (not all file paths)")
            else:
                new_lines.append(lines[i])
                i += 1
        else:
            new_lines.append(lines[i])
            i += 1

    if modified:
        with open(filepath, 'w') as f:
            f.writelines(new_lines)
        # Show the diff of what was changed
        show_git_diff(filepath, original_content)

        # File is fully resolved only if we modified it and have no unresolved conflicts
        fully_resolved = not has_unresolved_conflicts
        return fully_resolved

    return False


def find_files_with_conflicts(repo_root: Path) -> List[Tuple[Path, FileFormat]]:
    """Find all CMake, BUCK, and C++ files with merge conflicts."""
    files_with_conflicts = []

    # Find CMake files
    cmake_dir = repo_root / 'cmake'
    if cmake_dir.exists():
        for cmake_file in cmake_dir.glob('*.cmake'):
            with open(cmake_file, 'r') as f:
                content = f.read()
                if '<<<<<<< HEAD' in content:
                    files_with_conflicts.append((cmake_file, FileFormat.CMAKE))

    # Find BUCK files
    for buck_file in repo_root.rglob('BUCK'):
        # Skip hidden directories and build directories
        if any(part.startswith('.') or part in ['build', 'tmp_bld_dir'] for part in buck_file.parts):
            continue
        try:
            with open(buck_file, 'r') as f:
                content = f.read()
                if '<<<<<<< HEAD' in content:
                    files_with_conflicts.append((buck_file, FileFormat.BUCK))
        except (IOError, UnicodeDecodeError):
            # Skip files that can't be read
            continue

    # Find C++ files with conflicts (e.g. in #include lists). Grep tracked
    # files for conflict markers rather than relying on the index's unmerged
    # state, since files may have been (partially) staged already.
    result = subprocess.run(
        ['git', 'grep', '-l', '<<<<<<< HEAD', '--',
         '*.cpp', '*.h', '*.hpp', '*.cc'],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    for rel_path in result.stdout.splitlines():
        cpp_file = repo_root / rel_path
        if not cpp_file.exists():
            continue
        try:
            with open(cpp_file, 'r') as f:
                if '<<<<<<< HEAD' in f.read():
                    files_with_conflicts.append((cpp_file, FileFormat.CPP_INCLUDE))
        except (IOError, UnicodeDecodeError):
            # Skip files that can't be read
            continue

    return files_with_conflicts


def dedupe_file_lists(repo_root: Path) -> List[Path]:
    """
    Drop exact duplicate entries within each contiguous run of file-path lines
    (i.e. within one source list) of every cmake/BUCK build file.

    Conflict-hunk union is not the only way a sync merge mints duplicates: a
    clean git merge also keeps both copies when internal and upstream add the
    same entry at nearby-but-different positions in non-overlapping hunks.
    CMake and Buck silently tolerate duplicate sources, so nothing downstream
    ever fails. Files still containing conflict markers are skipped.

    Returns the list of modified files.
    """
    candidates: List[Tuple[Path, FileFormat]] = []
    cmake_dir = repo_root / 'cmake'
    if cmake_dir.exists():
        candidates += [(f, FileFormat.CMAKE) for f in sorted(cmake_dir.glob('*.cmake'))]
    for buck_file in sorted(repo_root.rglob('BUCK')):
        if any(part.startswith('.') or part in ['build', 'tmp_bld_dir'] for part in buck_file.parts):
            continue
        candidates.append((buck_file, FileFormat.BUCK))

    changed: List[Path] = []
    for filepath, file_format in candidates:
        try:
            with open(filepath, 'r') as fh:
                lines = fh.readlines()
        except (OSError, UnicodeDecodeError):
            continue
        if any(line.startswith('<<<<<<<') for line in lines):
            continue
        out_lines: List[str] = []
        seen: Set[str] = set()
        modified = False
        for line in lines:
            if is_file_path_line(line, file_format) and line.strip():
                paths = extract_file_paths([line], file_format)
                if paths and paths <= seen:
                    modified = True
                    print(f"  ✓ Dropped duplicate {next(iter(paths))} from {filepath.relative_to(repo_root)}")
                    continue
                seen |= paths
            else:
                # Non-path line = list boundary; entries may legitimately
                # repeat across different targets, so reset the run.
                seen = set()
            out_lines.append(line)
        if modified:
            with open(filepath, 'w') as fh:
                fh.writelines(out_lines)
            changed.append(filepath)
    return changed


def main():
    # Find repository root
    repo_root = Path(__file__).resolve().parent.parent.parent

    # Find all files with conflicts
    files_with_conflicts = find_files_with_conflicts(repo_root)

    if not files_with_conflicts:
        print("No merge conflicts found in CMake, BUCK, or C++ files.")
        deduped = dedupe_file_lists(repo_root)
        if deduped:
            subprocess.run(['git', 'add'] + [str(f) for f in deduped], check=True)
            print(f"Deduplicated file lists in {len(deduped)} file(s).")
        return

    # Group by file type for reporting
    cmake_files = [(f, fmt) for f, fmt in files_with_conflicts if fmt == FileFormat.CMAKE]
    buck_files = [(f, fmt) for f, fmt in files_with_conflicts if fmt == FileFormat.BUCK]
    cpp_files = [(f, fmt) for f, fmt in files_with_conflicts if fmt == FileFormat.CPP_INCLUDE]

    print(f"Found {len(files_with_conflicts)} file(s) with conflicts:")
    if cmake_files:
        print(f"\n  CMake files ({len(cmake_files)}):")
        for f, _ in cmake_files:
            print(f"    - {f.relative_to(repo_root)}")
    if buck_files:
        print(f"\n  BUCK files ({len(buck_files)}):")
        for f, _ in buck_files:
            print(f"    - {f.relative_to(repo_root)}")
    if cpp_files:
        print(f"\n  C++ files ({len(cpp_files)}):")
        for f, _ in cpp_files:
            print(f"    - {f.relative_to(repo_root)}")
    print()

    # Process each file
    fully_resolved_files = []
    for filepath, file_format in files_with_conflicts:
        print(f"Processing {filepath.relative_to(repo_root)}...")
        if process_file(filepath, repo_root, file_format):
            fully_resolved_files.append(filepath)

    # Clean-merge dedup pass: a merge can duplicate list entries without any
    # conflict, so sweep all build files (skips ones still holding markers).
    print("\nDeduplicating file lists...")
    deduped = dedupe_file_lists(repo_root)

    # Stage fully resolved and deduplicated files
    to_stage = fully_resolved_files + [f for f in deduped if f not in fully_resolved_files]
    if to_stage:
        print(f"\nStaging {len(to_stage)} file(s)...")
        subprocess.run(['git', 'add'] + [str(f) for f in to_stage], check=True)
        for filepath in to_stage:
            print(f"  ✓ Staged {filepath.relative_to(repo_root)}")

    print(f"\nDone! Resolved conflicts in {len(fully_resolved_files)} file(s), deduplicated {len(deduped)} file(s).")


if __name__ == '__main__':
    main()
