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
from typing import List, Set, Tuple, Optional
from enum import Enum
import subprocess


class FileFormat(Enum):
    """File format types for different build systems."""
    CMAKE = "cmake"
    BUCK = "buck"


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

    elif file_format == FileFormat.BUCK:
        # BUCK files use quoted strings with commas
        # Should not contain BUCK keywords or other syntax (except quotes and commas)
        if any(keyword in stripped for keyword in ['load(', 'name =', 'srcs =', 'headers =', 'deps =', 'visibility =', 'cpp_library(', 'cpp_binary(']):
            return False
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
        if stripped and not stripped.startswith('#'):
            if file_format == FileFormat.BUCK:
                # Extract path from quoted string, removing quotes and trailing comma
                if stripped.startswith('"'):
                    path = stripped.strip('",').strip('"')
                    paths.add(path)
            else:
                # CMake format - just use the stripped line
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


def resolve_conflict(ours_lines: List[str], theirs_lines: List[str], repo_root: Path, base_dir: Path, file_format: FileFormat) -> Optional[List[str]]:
    """
    Resolve a conflict by taking the union of file paths.

    Returns the resolved lines, or None if the conflict can't be auto-resolved.
    """
    # Check if all lines are file paths
    for line in ours_lines + theirs_lines:
        if not is_file_path_line(line, file_format):
            return None

    # Extract file paths from both sides
    ours_paths = extract_file_paths(ours_lines, file_format)
    theirs_paths = extract_file_paths(theirs_lines, file_format)

    # Take the union
    all_paths = ours_paths | theirs_paths

    # Filter out non-existent files
    existing_paths = {path for path in all_paths if file_exists(path, repo_root, base_dir)}

    # Sort alphabetically
    sorted_paths = sorted(existing_paths)

    # Format based on file type
    if file_format == FileFormat.CMAKE:
        # CMake format: 2-space indentation
        resolved_lines = [f"  {path}\n" for path in sorted_paths]
    else:  # BUCK format
        # BUCK format: 8-space indentation, quoted strings with trailing commas
        resolved_lines = [f'        "{path}",\n' for path in sorted_paths]

    return resolved_lines


def show_git_diff(file_path: Path) -> None:
    """Show the git diff for a file that was modified."""
    try:
        result = subprocess.run(
            ['git', 'diff', str(file_path)],
            capture_output=True,
            text=True,
            check=False
        )
        if result.stdout:
            print(f"\n  Changes made to {file_path}:")
            print("  " + "\n  ".join(result.stdout.splitlines()))
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

    modified = False
    i = 0
    new_lines = []

    while i < len(lines):
        if lines[i].startswith('<<<<<<< HEAD'):
            result = parse_conflict_block(lines, i)
            if result:
                start_idx, ours_lines, theirs_lines, end_idx = result
                resolved = resolve_conflict(ours_lines, theirs_lines, repo_root, base_dir, file_format)

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
        show_git_diff(filepath)

    return modified


def find_files_with_conflicts(repo_root: Path) -> List[Tuple[Path, FileFormat]]:
    """Find all CMake and BUCK files with merge conflicts."""
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

    return files_with_conflicts


def main():
    # Find repository root
    repo_root = Path(__file__).resolve().parent.parent.parent

    # Find all files with conflicts
    files_with_conflicts = find_files_with_conflicts(repo_root)

    if not files_with_conflicts:
        print("No merge conflicts found in CMake or BUCK files.")
        return

    # Group by file type for reporting
    cmake_files = [(f, fmt) for f, fmt in files_with_conflicts if fmt == FileFormat.CMAKE]
    buck_files = [(f, fmt) for f, fmt in files_with_conflicts if fmt == FileFormat.BUCK]

    print(f"Found {len(files_with_conflicts)} file(s) with conflicts:")
    if cmake_files:
        print(f"\n  CMake files ({len(cmake_files)}):")
        for f, _ in cmake_files:
            print(f"    - {f.relative_to(repo_root)}")
    if buck_files:
        print(f"\n  BUCK files ({len(buck_files)}):")
        for f, _ in buck_files:
            print(f"    - {f.relative_to(repo_root)}")
    print()

    # Process each file
    total_resolved = 0
    for filepath, file_format in files_with_conflicts:
        print(f"Processing {filepath.relative_to(repo_root)}...")
        if process_file(filepath, repo_root, file_format):
            total_resolved += 1

    print(f"\nDone! Resolved conflicts in {total_resolved} file(s).")


if __name__ == '__main__':
    main()
