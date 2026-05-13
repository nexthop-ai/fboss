"""JUnit XML writer matching the format produced by Google Test (gtest) binaries.

Schema (per gtest's XML output):
  <testsuites name="AllTests" tests="..." failures="..." disabled="..."
              errors="..." time="..." timestamp="...">
    <testsuite name="..." tests="..." failures="..." disabled="..."
               errors="..." time="..." timestamp="...">
      <testcase name="..." status="run" result="completed" time="..."
                timestamp="..." classname="...">
        <failure message="..." type=""/>   <!-- only present on failure -->
      </testcase>
    </testsuite>
  </testsuites>
"""

import os
import xml.etree.ElementTree as ET
from datetime import datetime, timezone


def write_junit(
    suite_name: str,
    results: list[tuple[str, bool, str]],
    path: str,
    total_time: float = 0.0,
) -> None:
    """Write a gtest-compatible JUnit XML file.

    Args:
        suite_name: value for <testsuite name=...> and per-case classname.
        results: list of (testcase_name, passed, message) tuples.
        path: output file path; parent dirs are created if missing.
        total_time: total elapsed seconds, written as the suite `time` attr.
    """
    failures = sum(1 for _, ok, _ in results if not ok)
    timestamp = datetime.now(timezone.utc).isoformat()
    common = {
        "tests": str(len(results)),
        "failures": str(failures),
        "disabled": "0",
        "errors": "0",
        "skipped": "0",
        "time": f"{total_time:.3f}",
        "timestamp": timestamp,
    }
    testsuites = ET.Element("testsuites", {"name": "AllTests", **common})
    suite = ET.SubElement(testsuites, "testsuite", {"name": suite_name, **common})
    for name, ok, msg in results:
        tc = ET.SubElement(
            suite,
            "testcase",
            {
                "name": name,
                "status": "run",
                "result": "completed",
                "time": "0",
                "timestamp": timestamp,
                "classname": suite_name,
            },
        )
        if not ok:
            ET.SubElement(tc, "failure", {"message": msg, "type": ""})
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    ET.ElementTree(testsuites).write(path, encoding="utf-8", xml_declaration=True)
