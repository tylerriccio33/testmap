import pytest
from testmap.discover import discover

SOURCE = """
from pytest_testmap import testmap
import pytest


@testmap(feature="parser", kind="unit")
def test_parser_unit(): ...


@pytest.mark.testmap(feature="parser", kind="integration")
def test_parser_integration(): ...


def test_untagged(): ...
"""


def test_discover_reads_both_decorator_forms(tmp_path) -> None:
    (tmp_path / "test_suite.py").write_text(SOURCE)

    records = discover([tmp_path], root=tmp_path)

    assert [(r["feature"], r["kind"]) for r in records] == [
        ("parser", "integration"),
        ("parser", "unit"),
    ]
    assert records[0]["nodeid"] == "test_suite.py::test_parser_integration"


def test_discover_skips_unparseable_files(tmp_path) -> None:
    (tmp_path / "broken.py").write_text("def oops(:\n")
    (tmp_path / "ok.py").write_text(
        "from pytest_testmap import testmap\n\n"
        '@testmap(feature="a", kind="unit")\n'
        "def test_a(): ...\n"
    )

    records = discover([tmp_path], root=tmp_path)

    assert [r["feature"] for r in records] == ["a"]


def test_discover_requires_feature_and_kind(tmp_path) -> None:
    (tmp_path / "test_bad.py").write_text(
        'from pytest_testmap import testmap\n\n@testmap(feature="a")\ndef test_a(): ...\n'
    )

    with pytest.raises(ValueError, match="requires string feature and kind"):
        discover([tmp_path], root=tmp_path)
