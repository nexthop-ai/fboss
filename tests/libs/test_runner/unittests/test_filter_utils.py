"""filter_utils.py: deriving one test module's filters from its siblings'."""

import pytest

from tests.libs.test_runner.filter_utils import (
    catch_all_filters,
    load_test_context,
    module_inclusion_filters,
    sibling_inclusion_filters,
)


class TestLoadTestContext:
    def test_reads_the_module_attribute(self, tmp_path):
        module = tmp_path / "bucket.py"
        module.write_text('test_context = {"filters": ["*A*"], "variant": "2x400G"}\n')
        assert load_test_context(str(module)) == {"filters": ["*A*"], "variant": "2x400G"}

    def test_calls_the_builder_when_filters_are_derived(self, tmp_path):
        module = tmp_path / "rest.py"
        module.write_text('def _build_test_context():\n    return {"filters": ["*"]}\n')
        assert load_test_context(str(module)) == {"filters": ["*"]}

    def test_neither_is_empty(self, tmp_path):
        module = tmp_path / "plain.py"
        module.write_text("x = 1\n")
        assert load_test_context(str(module)) == {}

    def test_syntax_error_propagates(self, tmp_path):
        module = tmp_path / "broken.py"
        module.write_text("test_context = {\n")
        with pytest.raises(SyntaxError):
            load_test_context(str(module))


class TestModuleInclusionFilters:
    def test_stops_at_first_exclusion(self, tmp_path):
        module = tmp_path / "bucket.py"
        module.write_text('test_context = {"filters": ["*A*", "*B*", "-*C*", "*D*"]}\n')
        assert module_inclusion_filters(str(module)) == ["*A*", "*B*"]

    def test_no_filters_key(self, tmp_path):
        module = tmp_path / "bucket.py"
        module.write_text("test_context = {}\n")
        assert module_inclusion_filters(str(module)) == []


class TestSiblingInclusionFilters:
    def test_unions_in_order_without_duplicates_and_skips_self(self, tmp_path):
        (tmp_path / "__init__.py").write_text("")
        (tmp_path / "one.py").write_text('test_context = {"filters": ["*A*", "-*Z*"]}\n')
        (tmp_path / "two.py").write_text('test_context = {"filters": ["*A*", "*B*"]}\n')
        (tmp_path / "notes.txt").write_text("not a module")
        rest = tmp_path / "rest.py"
        rest.write_text('test_context = {"filters": ["*NeverIncluded*"]}\n')
        assert sibling_inclusion_filters(str(rest), str(tmp_path)) == ["*A*", "*B*"]

    def test_spans_directories(self, tmp_path):
        a, b = tmp_path / "a", tmp_path / "b"
        a.mkdir()
        b.mkdir()
        (a / "one.py").write_text('test_context = {"filters": ["*A*"]}\n')
        (b / "two.py").write_text('test_context = {"filters": ["*B*", "*A*"]}\n')
        rest = a / "rest.py"
        rest.write_text("")
        assert sibling_inclusion_filters(str(rest), str(a), str(b)) == ["*A*", "*B*"]


class TestCatchAllFilters:
    def test_inverts_siblings(self, tmp_path):
        (tmp_path / "one.py").write_text('test_context = {"filters": ["*A*", "-*Z*"]}\n')
        (tmp_path / "two.py").write_text('test_context = {"filters": ["*B*"]}\n')
        rest = tmp_path / "rest.py"
        rest.write_text("")

        # Only the first exclusion carries the "-"; sibling exclusions are not
        # inherited, so "*Z*" must not appear.
        assert catch_all_filters(str(rest), str(tmp_path)) == ["*", "-*A*", "*B*"]

    def test_dedupes_and_skips_self(self, tmp_path):
        (tmp_path / "one.py").write_text('test_context = {"filters": ["*A*"]}\n')
        (tmp_path / "two.py").write_text('test_context = {"filters": ["*A*", "*B*"]}\n')
        rest = tmp_path / "rest.py"
        rest.write_text('test_context = {"filters": ["*NeverExcluded*"]}\n')

        assert catch_all_filters(str(rest), str(tmp_path)) == ["*", "-*A*", "*B*"]

    def test_alone_selects_everything(self, tmp_path):
        rest = tmp_path / "rest.py"
        rest.write_text("")
        assert catch_all_filters(str(rest), str(tmp_path)) == ["*"]
