# Copyright Meta Platforms, Inc. and affiliates.
# @noautodeps
"""Tests for TestRunner orchestration: _run_test, _run_tests, and related
end-to-end execution paths (gtest output post-processing, synthesize-OK
fallback for early-exit binaries), plus the _load_from_file helper consumed
by _get_tests_to_run via args.filter_file."""

import os
import tempfile
from unittest.mock import patch

from run_test import _load_from_file


class TestLoadFromFile:
    """_load_from_file is a module-level helper used by _get_tests_to_run
    (args.filter_file path) and BenchmarkTestRunner. Tests live here next to
    the consumer."""

    def test_basic(self):
        """Test loading entries from a file with comments and blank lines"""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".conf") as f:
            f.write("# Comment line\n")
            f.write("entry1\n")
            f.write("\n")
            f.write("entry2\n")
            f.write("# Another comment\n")
            f.write("entry3\n")
            temp_file = f.name
        try:
            result = _load_from_file(temp_file)
            assert result == ["entry1", "entry2", "entry3"]
        finally:
            os.unlink(temp_file)

    def test_nonexistent(self):
        """Test loading from a nonexistent file returns empty list"""
        result = _load_from_file("/nonexistent/path.conf")
        assert result == []

    def test_empty(self):
        """Test loading from an empty file returns empty list"""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".conf") as f:
            temp_file = f.name
        try:
            result = _load_from_file(temp_file)
            assert result == []
        finally:
            os.unlink(temp_file)

    def test_with_profile(self):
        """Test loading with profile filters to matching tagged lines"""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".conf") as f:
            f.write("entry_untagged\n")
            f.write("entry_tagged_p1 p1\n")
            f.write("entry_tagged_p2 p2\n")
            f.write("entry_tagged_t t\n")
            temp_file = f.name
        try:
            result = _load_from_file(temp_file, profile="p1")
            assert result == ["entry_tagged_p1"]
        finally:
            os.unlink(temp_file)

    def test_no_profile_includes_untagged_and_t(self):
        """Test that without profile, untagged and t-tagged lines are included"""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".conf") as f:
            f.write("entry_untagged\n")
            f.write("entry_tagged_p1 p1\n")
            f.write("entry_tagged_t t\n")
            temp_file = f.name
        try:
            result = _load_from_file(temp_file)
            assert result == ["entry_untagged", "entry_tagged_t"]
        finally:
            os.unlink(temp_file)

    def test_comments_and_whitespace(self):
        """Test that comments and whitespace-only lines are skipped"""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".conf") as f:
            f.write("# full comment\n")
            f.write("   \n")
            f.write("\n")
            f.write("  # indented comment\n")
            f.write("entry1\n")
            temp_file = f.name
        try:
            result = _load_from_file(temp_file)
            assert result == ["entry1"]
        finally:
            os.unlink(temp_file)


def _make_capture_writing(stdout_bytes: bytes, runner, xml_to_write: bytes | None):
    """Build a fake `_capture_subprocess` that optionally writes a gtest XML
    to runner.TESTRESULT_CURRENT_RUN_FILE and returns
    (returncode=0, timed_out=False, stdout_bytes, b"").
    """

    def fake_capture(cmd, timeout):  # noqa: ARG001 - signature mirrors _capture_subprocess
        if xml_to_write is not None:
            with open(runner.TESTRESULT_CURRENT_RUN_FILE, "wb") as f:
                f.write(xml_to_write)
        return 0, False, stdout_bytes, b""

    return fake_capture


_STUB_GTEST_XML = b"""<?xml version="1.0" encoding="UTF-8"?>
<testsuites tests="1" failures="0" errors="0" time="0.1">
  <testsuite name="HwFooTest" tests="1" failures="0">
    <testcase name="Bar" classname="HwFooTest" time="0.1" status="run"/>
  </testsuite>
</testsuites>
"""


class TestRunTestGtestFallback:
    """Tests for _run_test gtest output post-processing (prefix injection,
    synthesize-OK fallback for empty output)."""

    def test_preserves_skipped_does_not_synthesize_ok(
        self, runner, mock_args, tmp_path
    ):
        """End-to-end: a SKIPPED gtest result must not be rewritten as OK."""
        runner.TESTRESULT_CURRENT_RUN_FILE = str(tmp_path / "tr_current_run.xml")
        # _get_test_run_cmd reads the module-level `args` global, which is only
        # bound under `if __name__ == "__main__":` — use create=True to inject it.
        with (
            patch("run_test.args", new=mock_args, create=True),
            patch.object(
                runner,
                "_capture_subprocess",
                new=_make_capture_writing(
                    b"[  SKIPPED ] HwFooTest.Bar (5 ms)\n",
                    runner,
                    _STUB_GTEST_XML,
                ),
            ),
        ):
            result = runner._run_test(
                conf_file="dummy.conf",
                test_prefix="cold_boot.",
                test_to_run="HwFooTest.Bar",
                setup_warmboot=False,
                sai_logging="WARN",
                fboss_logging="WARN",
            )
        decoded = result.decode("utf-8")
        assert "SKIPPED" in decoded
        assert "cold_boot.HwFooTest.Bar" in decoded
        # Critical: the fallback must NOT have rewritten this to "[       OK ]".
        assert "[       OK ]" not in decoded

    def test_synthesize_ok_when_no_gtest_line(self, runner, mock_args, tmp_path):
        """Fallback path still works: empty output (e.g. --setup-for-warmboot early
        exit) should still synthesize an OK result so the test isn't lost from
        the summary."""
        runner.TESTRESULT_CURRENT_RUN_FILE = str(tmp_path / "tr_current_run.xml")
        with (
            patch("run_test.args", new=mock_args, create=True),
            patch.object(
                runner,
                "_capture_subprocess",
                new=_make_capture_writing(b"", runner, _STUB_GTEST_XML),
            ),
        ):
            result = runner._run_test(
                conf_file="dummy.conf",
                test_prefix="warm_boot.",
                test_to_run="HwFooTest.Bar",
                setup_warmboot=True,
                sai_logging="WARN",
                fboss_logging="WARN",
            )
        decoded = result.decode("utf-8")
        assert "[       OK ] warm_boot.HwFooTest.Bar" in decoded
