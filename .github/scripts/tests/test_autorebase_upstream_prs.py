"""Unit tests for autorebase_upstream_prs.py's eligibility rules.

Run with:  python3 -m pytest .github/scripts/tests/test_autorebase_upstream_prs.py
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_SPEC = importlib.util.spec_from_file_location(
    "autorebase_upstream_prs", Path(__file__).resolve().parent.parent / "autorebase_upstream_prs.py"
)
mod = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(mod)


def make_pr(**overrides) -> dict:
    pr = {
        "state": "open",
        "labels": [{"name": "CLA Signed"}, {"name": "nexthop"}],
        "head": {"repo": {"full_name": "nexthop-ai/fboss"}},
        "base": {"ref": "main"},
        "user": {"login": "Alice-Nexthop"},
    }
    pr.update(overrides)
    return pr


def comment(login: str | None, body: str) -> dict:
    return {"user": {"login": login} if login is not None else None, "body": body}


def no_comments_expected():
    raise AssertionError("comments must not be fetched for an ineligible PR")


def test_eligible():
    assert mod.evaluate(make_pr(), lambda: [comment("alice-nexthop", "please /autorebase")]) is None


@pytest.mark.parametrize(
    "labels", [[{"name": "CLA Signed"}], [{"name": "nexthop"}], []], ids=["no-nexthop", "no-cla", "none"]
)
def test_both_labels_required(labels):
    assert "missing label" in mod.evaluate(make_pr(labels=labels), no_comments_expected)


def test_closed_pr_skipped():
    assert "state" in mod.evaluate(make_pr(state="closed"), no_comments_expected)


@pytest.mark.parametrize("full_name", ["someone/fboss", "nexthop-ai/fboss-other", "Nexthop-AI/fboss", "facebook/fboss"])
def test_foreign_head_repo_skipped(full_name):
    pr = make_pr(head={"repo": {"full_name": full_name}})
    assert "head repo is" in mod.evaluate(pr, no_comments_expected)


def test_deleted_head_repo_skipped():
    assert "head repo is" in mod.evaluate(make_pr(head={"repo": None}), no_comments_expected)


def test_stacked_pr_skipped():
    assert "stacked" in mod.evaluate(make_pr(base={"ref": "alice.parent-branch"}), no_comments_expected)


def test_comment_from_non_author_ignored():
    comments = [comment("maintainer", "/autorebase"), comment("Alice-Nexthop", "lgtm")]
    assert "no /autorebase comment" in mod.evaluate(make_pr(), lambda: comments)


def test_ghost_author_never_matches_ghost_comment():
    assert "no /autorebase comment" in mod.evaluate(make_pr(user=None), lambda: [comment(None, "/autorebase")])


@pytest.mark.parametrize(
    "body,expected",
    [
        ("/autorebase", True),
        ("Hey bot:\n/autorebase\nthanks", True),
        ("`/autorebase`", True),
        ("/autorebase.", True),
        ("/autorebased already", False),
        ("/autorebase-later", False),
        ("see https://example.com/autorebase", False),
        ("autorebase", False),
    ],
)
def test_command_matching(body, expected):
    assert mod.author_opted_in("alice", [comment("alice", body)]) is expected
