#!/usr/bin/env python3
"""Offline checks for drift.py grouping. Run: python3 test_drift.py"""
import importlib.util, pathlib
spec = importlib.util.spec_from_file_location("drift", pathlib.Path(__file__).with_name("drift.py"))
d = importlib.util.module_from_spec(spec); spec.loader.exec_module(d)

# area_of takes a command DIRECTORY (no file name). config+delete share a key; show keeps its verb.
cases = {
    "commands/config/vlan": "vlan",
    "commands/delete/interface": "interface",
    "commands/show/interface": "show/interface",
    "commands/show/bgp/summary": "show/bgp",
    "commands/config/protocol/bgp/policy/as-path-list": "protocol/bgp",
    "commands/config/protocol/static": "protocol/static",
    "commands/delete/copp/cpu_traffic_policy": "copp",
    "commands/config": "config",
}
for path, want in cases.items():
    got = d.area_of(path.split("/"))
    assert got == want, f"{path}: got {got!r}, want {want!r}"

# generic directory grouping (any --scope that is not the CLI)
d.set_grouping("fboss/agent", "auto", 2)
assert d.GROUPING == "dir"
for rel, want in {"hw/sai/SaiSwitch.cpp": "hw/sai", "hw/sai/api/Foo.h": "hw/sai",
                  "state/Port.h": "state", "SwSwitch.cpp": "root"}.items():
    assert d.dir_group(rel) == want, (rel, d.dir_group(rel))
d.set_grouping("fboss/cli/fboss2", "auto", 2)
assert d.GROUPING == "cli"
assert d.is_test("test/config/FooTest.cpp") and not d.is_test("commands/config/Foo.h")

# split_diff cuts on file boundaries, never inside a file
diff = "diff --git a/x b/x\n" + "+a\n" * 10 + "diff --git a/y b/y\n" + "+b\n" * 10
chunks = d.split_diff(diff, max_lines=12)
assert len(chunks) == 2 and all(c.startswith("diff --git") for c in chunks), chunks

# redaction
import re
d.REDACT = re.compile(r"\b(lab\d+|dut\d+)\b|[\w.-]+\.example\.internal")   # the --redact default is org-specific
assert d.REDACT.sub("<R>", "on lab123 and dut7 and host.example.internal") == "on <R> and <R> and <R>"
print("ok")
