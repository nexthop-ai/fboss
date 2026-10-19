#!/usr/bin/env python3
"""Offline end-to-end checks. Run: python3 test_fresh_audit.py"""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import github_data

SCRIPTS = Path(__file__).resolve().parent
FILE = "fboss/cli/fboss2/commands/config/example/Example.cpp"


class FreshAuditTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        self.out = self.root / "audit"
        self.git("init", "-q")
        self.git("config", "user.name", "Audit test")
        self.git("config", "user.email", "audit@example.invalid")
        path = self.repo / FILE
        path.parent.mkdir(parents=True)
        path.write_text("OldBehavior();\n")
        self.git("add", ".")
        self.git("commit", "-qm", "base")
        self.git("update-ref", "refs/remotes/upstream/main", "HEAD")
        path.write_text("FreshBehavior();\n")
        self.git("commit", "-qam", "ours")
        self.git("update-ref", "refs/remotes/origin/main", "HEAD")
        self.state = self.root / "github.json"
        self.set_github()
        bindir = self.root / "bin"
        bindir.mkdir()
        gh = bindir / "gh"
        gh.write_text(f"#!{sys.executable}\n" + '''
import json, os, sys
from pathlib import Path
state = json.loads(Path(os.environ["AUDIT_GITHUB_STATE"]).read_text())
if state.get("fail"):
    print("GitHub unavailable", file=sys.stderr)
    sys.exit(1)
args = sys.argv[1:]
if args[:2] == ["pr", "diff"]:
    print(state["diff"])
elif any("/files?" in a for a in args):
    print("\\n".join(state["files"]))
elif args[0] == "api":
    if state["open"]:
        print(json.dumps({"number": 123, "title": "Example change",
                          "branch": "example", "repo": "example/fork"}))
else:
    raise SystemExit("Unexpected gh call: " + repr(args))
''')
        gh.chmod(0o755)
        self.env = dict(os.environ, PATH=str(bindir) + os.pathsep + os.environ["PATH"],
                        AUDIT_GITHUB_STATE=str(self.state))

    def git(self, *args):
        return subprocess.run(["git", *args], cwd=self.repo, capture_output=True,
                              text=True, check=True).stdout.strip()

    def set_github(self, **changes):
        state = {"open": True, "files": [FILE], "diff": "+FreshBehavior();\n+LiveProofToken();"}
        if self.state.exists():
            state.update(json.loads(self.state.read_text()))
        state.update(changes)
        self.state.write_text(json.dumps(state))

    def script(self, name, *args, input=None):
        return subprocess.run([sys.executable, str(SCRIPTS / name), *map(str, args)],
                              cwd=self.repo, env=self.env, input=input,
                              capture_output=True, text=True)

    def collect(self):
        result = self.script("drift.py", "--scope", "fboss/cli/fboss2", "--out", self.out,
                             "--repo", "example/upstream", "--fork", "example/fork")
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)

    def judge(self, evidence=None):
        item = {"group": "example", "verdict": "SUBMITTED", "effort": "S", "benefit": "S",
                "notes": "**Already upstream?**\n- #123 contains the change.\n\n**Steps:**\nChase #123.",
                "evidence": evidence or ["+FreshBehavior();"]}
        result = self.script("merge_verdicts.py", self.out, input=json.dumps(item) + "\n")
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads((self.out / "verdicts.json").read_text())["example"]

    def render(self):
        result = self.script("drift.py", "--render", "--out", self.out)
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)

    def test_full_workflow_creates_no_cache(self):
        self.collect()
        self.judge(["+LiveProofToken();"])
        self.render()
        for checker in ("verify_report.py", "validate_report.py"):
            result = self.script(checker, self.out)
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertFalse((self.out / "cache").exists())
        self.assertIn("Validated against git", (self.out / "report.md").read_text())

    def test_legacy_caches_cannot_supply_evidence(self):
        self.collect()
        old = self.out / "cache" / "prdiffs"
        old.mkdir(parents=True)
        (old / "123.diff").write_text("+ObsoleteCacheOnlyEvidence();\n")
        (old.parent / "prs.json").write_text("not even valid JSON")
        verdict = self.judge(["+ObsoleteCacheOnlyEvidence();"])
        self.assertEqual(verdict["evidence_verified"], "0/1")
        result = self.script("verify_report.py", self.out)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("evidence", result.stdout)

    def test_recollect_requires_all_groups_to_be_rejudged(self):
        self.collect()
        self.judge()
        self.collect()  # unchanged Git diff still needs fresh PR/semantic review
        self.assertEqual(json.loads((self.out / "verdicts.json").read_text()), {})
        self.assertIn("Judged: 0 / 1", (self.out / "report.md").read_text())
        self.assertNotIn("Since the last run", (self.out / "report.md").read_text())

    def test_both_checkers_detect_newly_closed_pr(self):
        self.collect()
        self.judge()
        self.render()
        self.set_github(open=False)
        for checker in ("verify_report.py", "validate_report.py"):
            result = self.script(checker, self.out)
            self.assertNotEqual(result.returncode, 0, checker + result.stdout)
            self.assertIn("#123", result.stdout)

    def test_verifier_refetches_changed_pr_evidence(self):
        self.collect()
        self.judge(["+LiveProofToken();"])
        self.assertEqual(self.script("verify_report.py", self.out).returncode, 0)
        self.set_github(diff="+FreshBehavior();")
        result = self.script("verify_report.py", self.out)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("LiveProofToken", result.stdout)

    def test_validator_refetches_changed_coverage(self):
        self.collect()
        self.judge()
        self.render()
        self.set_github(diff="+UnrelatedBehavior();")
        result = self.script("validate_report.py", self.out)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("FreshBehavior", result.stdout)

    def test_api_failure_never_falls_back_to_old_outputs(self):
        self.collect()
        self.judge()
        self.render()
        before = (self.out / "verdicts.json").read_text()
        self.set_github(fail=True)
        for name, args in (("drift.py", ("--scope", "fboss/cli/fboss2", "--out", self.out, "--repo", "example/upstream", "--fork", "example/fork")),
                           ("verify_report.py", (self.out,)), ("validate_report.py", (self.out,)),
                           ("merge_verdicts.py", (self.out,))):
            result = self.script(name, *args, input="")
            self.assertNotEqual(result.returncode, 0, name)
        self.assertEqual((self.out / "verdicts.json").read_text(), before)

    def test_failed_file_list_query_is_not_an_empty_success(self):
        listing = json.dumps({"number": 123, "title": "Example", "branch": "example", "repo": "example/fork"})
        with patch.object(github_data, "gh", side_effect=[listing, subprocess.CalledProcessError(1, "gh")]):
            with self.assertRaises(subprocess.CalledProcessError):
                github_data.open_upstream_prs("example/fork", "example/upstream")

    def test_render_propagates_live_validation_failure(self):
        self.collect()
        self.judge()
        self.set_github(fail=True)
        result = self.script("drift.py", "--render", "--out", self.out)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("VALIDATION FAILED", (self.out / "report.md").read_text())


if __name__ == "__main__":
    unittest.main()
