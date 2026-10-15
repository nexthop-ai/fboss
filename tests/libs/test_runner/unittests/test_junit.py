"""junit.py: multi-pass JUnit merge, result-name normalization, and the
benchmark CSV to tr.xml conversion. All pure local-file functions."""

import xml.etree.ElementTree as ET

import pytest

from tests.libs.test_runner.junit import (
    generate_tr_xml_from_csv,
    merge_junit_results,
    normalize_test_results_file,
)


def _write_pass(tmp_path, label, cases, *, timestamp="2026-10-14T10:00:00", time="1.5", failures=0):
    """One pass's log + tr.xml, the way run_test.py leaves them."""
    log = tmp_path / f"{label}.log"
    log.write_text(f"{label} log\n")
    suite = ET.Element("testsuite", {
        "tests": str(len(cases)), "failures": str(failures), "errors": "0",
        "disabled": "0", "skipped": "0", "time": time, "timestamp": timestamp, "name": "AllTests",
    })
    for classname, name in cases:
        ET.SubElement(suite, "testcase", {"name": name, "classname": classname, "time": "0.5"})
    root = ET.Element("testsuites")
    root.append(suite)
    xml = tmp_path / f"{label}.xml"
    ET.ElementTree(root).write(xml, encoding="UTF-8", xml_declaration=True)
    return label, str(log), str(xml)


def _suite(xml_path):
    return ET.parse(xml_path).getroot().find("testsuite")


class TestMergeJunitResults:
    def test_merges_passes_and_sums_totals(self, tmp_path):
        main = _write_pass(tmp_path, "main", [("HwTest", "a"), ("HwTest", "b")], time="1.5")
        optics = _write_pass(tmp_path, "optics", [("HwTest", "c")], timestamp="2026-10-14T11:00:00", time="2.25", failures=1)
        log, xml = tmp_path / "test.log", tmp_path / "tr.xml"

        merge_junit_results([main, optics], log_path=str(log), xml_path=str(xml))

        suite = _suite(xml)
        assert suite.get("name") == "AllTests"
        assert [tc.get("name") for tc in suite.findall("testcase")] == ["a", "b", "c"]
        assert suite.get("tests") == "3"
        assert suite.get("failures") == "1"
        assert suite.get("time") == "3.750"
        # The first pass with a timestamp wins.
        assert suite.get("timestamp") == "2026-10-14T10:00:00"
        text = log.read_text()
        assert "===== main pass =====\nmain log" in text
        assert "===== optics pass =====\noptics log" in text
        assert text.index("main pass") < text.index("optics pass")

    def test_skipped_patterns_become_skipped_testcases(self, tmp_path):
        main = _write_pass(tmp_path, "main", [("HwTest", "a")])
        log, xml = tmp_path / "test.log", tmp_path / "tr.xml"

        merge_junit_results(
            [main], skipped=[("*i2cStressWrite*", "no optics cabled")],
            log_path=str(log), xml_path=str(xml),
        )

        suite = _suite(xml)
        assert (suite.get("tests"), suite.get("skipped")) == ("2", "1")
        skipped = suite.findall("testcase")[-1]
        assert skipped.get("name") == "i2cStressWrite"
        assert skipped.get("classname") == "Skipped"
        assert skipped.find("skipped").get("message") == "no optics cabled"
        assert "===== pass skipped (no optics cabled): *i2cStressWrite* =====" in log.read_text()

    def test_no_passes_backfills_a_timestamp(self, tmp_path):
        log, xml = tmp_path / "test.log", tmp_path / "tr.xml"
        merge_junit_results([], skipped=[("*Foo*", "reason")], log_path=str(log), xml_path=str(xml))
        suite = _suite(xml)
        # An empty timestamp breaks the orchestrator's junit date parsing.
        assert suite.get("timestamp")
        assert suite.get("tests") == "1"

    def test_missing_and_unparseable_pass_files_are_tolerated(self, tmp_path):
        good = _write_pass(tmp_path, "main", [("HwTest", "a")])
        broken_xml = tmp_path / "optics.xml"
        broken_xml.write_text("<testsuites><testsuite")
        log, xml = tmp_path / "test.log", tmp_path / "tr.xml"

        merge_junit_results(
            [good, ("optics", str(tmp_path / "nope.log"), str(broken_xml)), ("strict", "/no/log", "/no/xml")],
            log_path=str(log), xml_path=str(xml),
        )

        suite = _suite(xml)
        assert suite.get("tests") == "1"
        assert "main pass" in log.read_text()


class TestNormalizeTestResultsFile:
    def _write(self, tmp_path, body):
        xml = tmp_path / "tr.xml"
        xml.write_text(
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<testsuites>\n'
            '  <testsuite tests="2" name="AllTests">\n'
            f"{body}"
            "  </testsuite>\n"
            "</testsuites>\n"
        )
        return xml

    def test_renames_suite_and_qualifies_testcase_names(self, tmp_path):
        xml = self._write(
            tmp_path,
            '    <testcase name="a" classname="HwPortTest" time="0.5" />\n'
            '    <testcase name="b" classname="HwTest/0" time="0.5" />\n',
        )

        normalize_test_results_file("t0_sai_tests", str(xml))

        suite = _suite(xml)
        assert suite.get("name") == "t0_sai_tests"
        assert [tc.get("name") for tc in suite.findall("testcase")] == ["HwPortTest.a", "HwTest.b"]

    def test_missing_file_is_a_noop(self, tmp_path):
        normalize_test_results_file("t0_sai_tests", str(tmp_path / "absent.xml"))

    @pytest.mark.xfail(raises=IndexError, strict=True, reason="line-based rewrite needs classname")
    def test_testcase_without_classname(self, tmp_path):
        xml = self._write(tmp_path, '    <testcase name="a" time="0.5" />\n')
        normalize_test_results_file("t0_sai_tests", str(xml))
        assert [tc.get("name") for tc in _suite(xml).findall("testcase")] == ["a"]


_CSV_HEADER = "benchmark_test_name,benchmark_binary_name,benchmark_time_ps,test_status,threshold_status,threshold_details\n"


class TestGenerateTrXmlFromCsv:
    def test_converts_rows_to_testcases(self, tmp_path):
        csv_path = tmp_path / "benchmark_results_x.csv"
        csv_path.write_text(
            _CSV_HEADER
            + "HwStatsCollection,sai_all_benchmarks,2000000000000,PASSED,OK,\n"
            + "HwRouteAdd,sai_all_benchmarks,500000000000,FAILED,OK,\n"
            + "HwInit,sai_all_benchmarks,,TIMEOUT,,\n"
            + "HwEcmp,sai_all_benchmarks,not-a-number,PASSED,EXCEEDED,p99 above 3ms\n"
            + "HwFib,sai_all_benchmarks,1000000000000,PASSED,EXCEEDED,\n"
        )
        xml = tmp_path / "tr.xml"

        assert generate_tr_xml_from_csv(str(csv_path), str(xml), "20261014_103000", skipped_count=2) is True

        suite = _suite(xml)
        assert suite.get("timestamp") == "2026-10-14T10:30:00.000"
        assert (suite.get("tests"), suite.get("failures"), suite.get("skipped")) == ("7", "4", "2")
        assert suite.get("time") == "3.500000"
        cases = {tc.get("name"): tc for tc in suite.findall("testcase")}
        assert cases["HwStatsCollection"].get("time") == "2.000000"
        assert cases["HwStatsCollection"].find("failure") is None
        assert cases["HwRouteAdd"].find("failure").get("message") == "test_status=FAILED"
        assert cases["HwInit"].get("result") == "timed-out"
        assert cases["HwInit"].find("failure").get("message") == "test_status=TIMEOUT"
        assert cases["HwEcmp"].get("time") == "0.000000"
        assert cases["HwEcmp"].find("failure").get("message") == "threshold exceeded: p99 above 3ms"
        assert cases["HwFib"].find("failure").get("message") == "threshold exceeded"
        assert all(tc.get("classname") == "Benchmarks" for tc in cases.values())

    def test_empty_csv_writes_an_empty_suite(self, tmp_path):
        csv_path = tmp_path / "benchmark_results_x.csv"
        csv_path.write_text(_CSV_HEADER)
        xml = tmp_path / "tr.xml"
        generate_tr_xml_from_csv(str(csv_path), str(xml), "20261014_103000")
        suite = _suite(xml)
        assert (suite.get("tests"), suite.get("failures")) == ("0", "0")
        assert suite.findall("testcase") == []

    def test_bad_timestamp_raises(self, tmp_path):
        csv_path = tmp_path / "x.csv"
        csv_path.write_text(_CSV_HEADER)
        with pytest.raises(ValueError):
            generate_tr_xml_from_csv(str(csv_path), str(tmp_path / "tr.xml"), "yesterday")
