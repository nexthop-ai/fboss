#!/usr/bin/env python3
# Copyright Meta Platforms, Inc. and affiliates.

"""Verify expected fboss systemd daemons are active and stable. Runs on the DUT.

Two phases, with shared budgets across all services to avoid bloating runtime.
  1. Startup: every service must reach its expected active count within
     --startup-timeout seconds (total, not per-service).
  2. Stability: sleep --stability-window seconds, then every service must
     still be active and have NRestarts == 0.
"""

import subprocess
import sys
import time
from argparse import ArgumentParser
from typing import NamedTuple

from junit import write_junit


class StartupState(NamedTuple):
    """Per-pattern startup snapshot. ``failure`` is empty on success."""

    actives: list[str]
    failure: str


HW_AGENT_WILDCARD = "fboss_hw_agent@*.service"
DEFAULT_SERVICES = [
    "platform_manager.service",
    "fboss_sw_agent.service",
    "qsfp_service.service",
    "fsdb.service",
    HW_AGENT_WILDCARD,
    # TODO BGP++
]
DEFAULT_RESULTS_XML = "/home/admin/tr.xml"
DEFAULT_STARTUP_TIMEOUT = 180
DEFAULT_STABILITY_WINDOW = 180
POLL_INTERVAL_SEC = 2


def _systemctl(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["systemctl", *args], capture_output=True, text=True, check=False
    )


def is_active(unit: str) -> bool:
    out = _systemctl("show", "-p", "ActiveState", "--value", "--", unit).stdout.strip()
    return out == "active"


def restart_count(unit: str) -> int:
    out = _systemctl("show", "-p", "NRestarts", "--value", "--", unit).stdout.strip()
    return int(out) if out.isdigit() else 0


def list_units(pattern: str) -> list[str]:
    """Expand a unit pattern (literal or wildcard) to matching unit names."""
    out = _systemctl("list-units", "--all", "--no-legend", "--plain", pattern).stdout
    return [line.split()[0] for line in out.splitlines() if line.strip()]


def _snapshot(targets: list[tuple[str, int]]) -> dict[str, StartupState]:
    """Check each target once."""
    snapshot: dict[str, StartupState] = {}
    for pattern, expected in targets:
        units = list_units(pattern)
        actives = [u for u in units if is_active(u)]
        if len(actives) >= expected:
            failure = ""
        elif expected == 1:
            failure = f"not active (units={units})"
        else:
            failure = f"only {len(actives)}/{expected} active (units={units})"
        snapshot[pattern] = StartupState(actives, failure)
    return snapshot


def wait_all_started(
    targets: list[tuple[str, int]], deadline: float
) -> dict[str, StartupState]:
    """Poll until every target has >=expected active units, or deadline hits."""
    while True:
        snapshot = _snapshot(targets)
        if all(not s.failure for s in snapshot.values()):
            return snapshot
        if time.monotonic() >= deadline:
            return snapshot
        time.sleep(POLL_INTERVAL_SEC)


def verify_stable(actives: list[str]) -> tuple[bool, str]:
    failures = []
    for unit in actives:
        if not is_active(unit):
            failures.append(f"{unit} went inactive")
            continue
        n = restart_count(unit)
        if n > 0:
            failures.append(f"{unit} restarted {n} time(s)")
    if failures:
        return False, "; ".join(failures)
    return True, f"stable ({len(actives)} active: {actives})"


def main(argv: list[str] | None = None) -> int:
    p = ArgumentParser(description=__doc__)
    p.add_argument(
        "--stability-window",
        type=int,
        default=DEFAULT_STABILITY_WINDOW,
        help="Seconds all services must remain active and not restart.",
    )
    p.add_argument(
        "--startup-timeout",
        type=int,
        default=DEFAULT_STARTUP_TIMEOUT,
        help="Total seconds (across all services) to reach expected active count.",
    )
    p.add_argument("--expected-hw-agents", type=int, default=1)
    p.add_argument(
        "--services",
        default=None,
        help="Comma-separated unit names; overrides default set.",
    )
    p.add_argument("--results-xml", default=DEFAULT_RESULTS_XML)
    args = p.parse_args(argv)

    services = (
        [s.strip() for s in args.services.split(",") if s.strip()]
        if args.services
        else DEFAULT_SERVICES
    )
    targets = [
        (s, args.expected_hw_agents if "fboss_hw_agent" in s else 1) for s in services
    ]

    started = time.monotonic()
    startup = wait_all_started(targets, deadline=started + args.startup_timeout)

    # If any service didn't come up, report startup state and skip the
    # stability window entirely — no point waiting to re-confirm failures.
    if any(state.failure for state in startup.values()):
        results = [
            (pattern, not state.failure, state.failure)
            for pattern, state in startup.items()
        ]
    else:
        time.sleep(args.stability_window)
        results = [
            (pattern, *verify_stable(state.actives))
            for pattern, state in startup.items()
        ]

    for pattern, ok, msg in results:
        print(f"[{'OK' if ok else 'FAIL'}] {pattern}: {msg}", flush=True)

    write_junit(
        "SmokeTest", results, args.results_xml, total_time=time.monotonic() - started
    )
    failed = sum(1 for _, ok, _ in results if not ok)
    print(f"\n{len(results) - failed} passed, {failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
