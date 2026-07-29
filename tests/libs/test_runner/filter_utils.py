"""Derive one test module's filters from its siblings'.

test_context["filters"] lists inclusions first; the first entry starting with "-"
begins the exclusions. A catch-all module inverts that -- "*" minus the union of
its siblings' inclusions -- so tests claimed nowhere else still run somewhere.
"""

import importlib.util
import os


def load_test_context(filepath):
    """Import a test module and return its test_context, calling the builder when
    the module derives its filters instead of stating them."""
    name = "_filter_src_" + os.path.splitext(os.path.basename(filepath))[0]
    spec = importlib.util.spec_from_file_location(name, filepath)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if hasattr(module, "test_context"):
        return module.test_context
    builder = getattr(module, "_build_test_context", None)
    return builder() if builder else {}


def module_inclusion_filters(filepath):
    """Return the inclusion regexes from a test module's test_context filters."""
    filters = load_test_context(filepath).get("filters", [])

    inclusions = []
    for regex in filters:
        if regex.startswith("-"):
            break
        inclusions.append(regex)
    return inclusions


def sibling_inclusion_filters(this_file, *directories):
    """Union the inclusion regexes of every test module in ``directories``,
    skipping ``this_file`` itself. Order is preserved and duplicates dropped."""
    inclusions = []
    for directory in directories:
        for filename in sorted(os.listdir(directory)):
            if not filename.endswith(".py") or filename == "__init__.py":
                continue
            filepath = os.path.join(directory, filename)
            if os.path.abspath(filepath) == os.path.abspath(this_file):
                continue
            for regex in module_inclusion_filters(filepath):
                if regex not in inclusions:
                    inclusions.append(regex)
    return inclusions


def catch_all_filters(this_file, *directories):
    """Build a test_context filters list matching everything the other modules in
    ``directories`` do not claim."""
    filters = ["*"]
    for i, regex in enumerate(sibling_inclusion_filters(this_file, *directories)):
        # Only the first exclusion carries the "-"; the rest follow it.
        filters.append(f"-{regex}" if i == 0 else regex)
    return filters
