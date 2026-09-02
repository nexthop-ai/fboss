"""JUnit XML result handling: multi-pass merge, name normalization, and
benchmark-CSV conversion. Pure local-file functions with no DUT or FBOSS
dependencies.
"""

import csv
import logging
import os
import xml.etree.ElementTree as ET
from datetime import datetime

logger = logging.getLogger("test_runner")


def merge_junit_results(
    passes: list[tuple[str, str, str]],
    skipped: list[tuple[str, str]] = (),
    log_path: str = "/tmp/test.log",
    xml_path: str = "/tmp/tr.xml",
) -> None:
    """Merge multiple (label, log_local, xml_local) pass results, plus a
    synthetic <skipped> testcase per (pattern, reason) in ``skipped``,
    into ``log_path`` and ``xml_path``.
    """
    testsuites_el = ET.Element("testsuites")
    merged = ET.SubElement(testsuites_el, "testsuite", {
        "tests": "0", "failures": "0", "errors": "0",
        "disabled": "0", "skipped": "0", "time": "0",
        "timestamp": "", "name": "AllTests",
    })
    totals = {"tests": 0, "failures": 0, "errors": 0, "disabled": 0, "skipped": 0}
    total_time = 0.0
    log_parts = []

    for label, log_local, xml_local in passes:
        if os.path.exists(log_local):
            with open(log_local, encoding="utf-8", errors="replace") as f:
                log_parts.append(f"\n===== {label} pass =====\n{f.read()}")
        if os.path.exists(xml_local):
            try:
                suite = ET.parse(xml_local).getroot().find("testsuite")
            except ET.ParseError as e:
                logger.warning(
                    "Failed to parse %s pass results %s: %s", label, xml_local, e
                )
                suite = None
            if suite is not None:
                for tc in suite.findall("testcase"):
                    merged.append(tc)
                for key in totals:
                    totals[key] += int(suite.get(key, 0) or 0)
                total_time += float(suite.get("time", 0) or 0)
                if not merged.get("timestamp"):
                    merged.set("timestamp", suite.get("timestamp", ""))

    for pattern, reason in skipped:
        tc = ET.SubElement(merged, "testcase", {
            "name": pattern.strip("*"), "classname": "Skipped", "time": "0",
        })
        ET.SubElement(tc, "skipped", {"message": reason})
        totals["tests"] += 1
        totals["skipped"] += 1
        log_parts.append(f"\n===== pass skipped ({reason}): {pattern} =====\n")

    for key, value in totals.items():
        merged.set(key, str(value))
    merged.set("time", f"{total_time:.3f}")
    if not merged.get("timestamp"):
        # No pass contributed a timestamp (every filter skipped); an empty
        # one breaks the orchestrator's junit date parsing.
        merged.set("timestamp", datetime.now().isoformat(timespec="seconds"))

    ET.indent(testsuites_el)
    ET.ElementTree(testsuites_el).write(xml_path, encoding="UTF-8", xml_declaration=True)
    with open(log_path, "w", encoding="utf-8") as f:
        f.write("\n".join(log_parts))


def normalize_test_results_file(suite_name: str, xml_path: str = "/tmp/tr.xml") -> None:
    """Normalize a test results XML file: name the suite after the test module
    and qualify each testcase name with its classname."""
    logger.info("Normalizing test results file")
    if not os.path.exists(xml_path):
        logger.warning("%s not found, skipping normalization", xml_path)
        return
    with open(xml_path, encoding="utf-8") as f:
        lines = f.readlines()

    with open(xml_path, "w", encoding="utf-8") as f:
        for line in lines:
            if line.strip().startswith("<testsuite"):
                line = line.replace('name="AllTests"', f'name="{suite_name}"')
            elif line.strip().startswith("<testcase"):
                classname = line.split('classname="')[1].split('"')[0]
                classname = classname.split("/")[0]
                name = line.split('name="')[1].split('"')[0]
                line = line.replace(f'name="{name}"', f'name="{classname}.{name}"')
            f.write(line)


def generate_tr_xml_from_csv(
    csv_path: str, xml_path: str, csv_timestamp: str, skipped_count: int = 0
) -> bool:
    """
    Convert a benchmark CSV into a minimal JUnit-style tr.xml.

    Args:
        csv_path: Path to benchmark_results_*.csv
        xml_path: Output XML path (e.g. /tmp/tr.xml)
        csv_timestamp: timestamp on the original CSV
        skipped_count: pre-filtered (known bad) benchmark count

    Returns:
        bool: if tr.xml creation was successful
    """

    # Convert original CSV timestamp to correct format
    suite_timestamp = datetime.strptime(csv_timestamp, "%Y%m%d_%H%M%S").strftime(
        "%Y-%m-%dT%H:%M:%S.%f"
    )[:-3]

    # Create XML tree
    testsuites_el = ET.Element("testsuites")
    testsuite_el = ET.SubElement(
        testsuites_el,
        "testsuite",
        {
            "tests": "0",  # filled later
            "failures": "0",  # filled later
            "disabled": "0",  # cannot be inferred from CSV
            "errors": "0",  # cannot be inferred from CSV
            "skipped": str(skipped_count),
            "time": "0.000",  # filled later
            "timestamp": suite_timestamp,
            "name": "AllTests",
        },
    )

    # Calculate stats that require row-by-row inspection
    total_failures = 0
    total_time_sec = 0.0

    with open(csv_path, mode="r") as f:
        rows = list(csv.DictReader(f))

    logger.info("Parsing CSV file...")

    for row in rows:
        # Benchmark names aren't structured as ClassName.testName
        name = row.get("benchmark_test_name")
        classname = "Benchmarks"
        # No obvious way to get the actual source file name;
        # using compiled binary as placeholder
        filename = row.get("benchmark_binary_name")

        # Benchmark time is in picoseconds; convert to seconds
        benchmark_time_ps = row.get("benchmark_time_ps", "")
        try:
            case_time_sec = (
                max(float(benchmark_time_ps) / 1e12, 0.0)
                if benchmark_time_ps
                else 0.0
            )
        except (TypeError, ValueError):
            case_time_sec = 0.0
        total_time_sec += case_time_sec

        # Get benchmark results
        test_status = (row.get("test_status") or "").upper()
        threshold_status = (row.get("threshold_status") or "").upper()
        threshold_details = row.get("threshold_details") or ""

        # Add testcase element
        testcase_el = ET.SubElement(
            testsuite_el,
            "testcase",
            {
                "name": name,
                "file": filename,
                "line": "",
                "status": "run",
                "result": "timed-out"
                if (test_status == "TIMEOUT")
                else "completed",
                "time": f"{case_time_sec:.6f}",
                "timestamp": suite_timestamp,  # Per-test timestamp not in CSV
                "classname": classname,
            },
        )

        # Add failure subelement if appropriate
        failure_reasons = []

        if test_status == "FAILED":
            failure_reasons.append("test_status=FAILED")
        elif test_status == "TIMEOUT":
            failure_reasons.append("test_status=TIMEOUT")

        if threshold_status == "EXCEEDED":
            if threshold_details:
                failure_reasons.append(f"threshold exceeded: {threshold_details}")
            else:
                failure_reasons.append("threshold exceeded")

        if failure_reasons:
            total_failures += 1
            message = "; ".join(failure_reasons)

            ET.SubElement(
                testcase_el,
                "failure",
                {"message": message},
            )

    total_tests = len(rows) + skipped_count

    testsuite_el.set("tests", str(total_tests))
    testsuite_el.set("failures", str(total_failures))
    testsuite_el.set("time", f"{total_time_sec:.6f}")

    logger.info("Successfully parsed CSV --> writing results to xml file")

    tree = ET.ElementTree(testsuites_el)
    ET.indent(tree, space=" ", level=0)
    tree.write(xml_path, encoding="UTF-8", xml_declaration=True)
    return True
