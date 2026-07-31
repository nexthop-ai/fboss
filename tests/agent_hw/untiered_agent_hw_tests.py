import importlib.util
import os


def _module_inclusion_filters(filepath):
    """Return the inclusion regexes from a test module's test_context filters.

    The module is imported and its test_context read directly. Each module's
    filters list inclusion regexes optionally followed by exclusion regexes. The
    first regex starting with "-" marks the start of the exclusion criteria, so
    everything before it (and nothing from it onwards) is an inclusion criterion.
    """
    name = "_untiered_filter_src_" + os.path.splitext(os.path.basename(filepath))[0]
    spec = importlib.util.spec_from_file_location(name, filepath)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    filters = getattr(module, "test_context", {}).get("filters", [])

    inclusions = []
    for regex in filters:
        if regex.startswith("-"):
            break
        inclusions.append(regex)
    return inclusions


def _build_test_context():
    """Build the untiered filter from every other agent_hw module.

    The untiered tests are everything not already covered by the tiered
    agent_hw modules, so the exclusion criteria are the union of those
    modules' inclusion criteria.
    """
    this_file = os.path.abspath(__file__)
    agent_hw_dir = os.path.dirname(this_file)

    exclusions = []
    for filename in sorted(os.listdir(agent_hw_dir)):
        if not filename.endswith(".py") or filename == "__init__.py":
            continue
        filepath = os.path.join(agent_hw_dir, filename)
        if os.path.abspath(filepath) == this_file:
            continue
        for regex in _module_inclusion_filters(filepath):
            if regex not in exclusions:
                exclusions.append(regex)

    filters = ["*"]
    for i, regex in enumerate(exclusions):
        filters.append(f"-{regex}" if i == 0 else regex)
    return {"filters": filters}


def test_untiered_agent_hw_tests(sai_agent_test_runner):
    assert sai_agent_test_runner.run_test(_build_test_context())
