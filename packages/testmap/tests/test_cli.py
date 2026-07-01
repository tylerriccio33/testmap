import json

import pytest
from testmap.cli import main

PYPROJECT = (
    "[tool.pytest.ini_options]\n"
    'testpaths = ["tests"]\n'
    "[tool.testmap]\n"
    'kinds = ["unit", "integration"]\n'
    'required = ["unit", "integration"]\n'
)

SUITE = (
    "from pytest_testmap import testmap\n\n"
    '@testmap(feature="parser", kind="unit")\n'
    "def test_a(): ...\n"
)


@pytest.fixture
def project(tmp_path, monkeypatch):
    (tmp_path / "pyproject.toml").write_text(PYPROJECT)
    tests = tmp_path / "tests"
    tests.mkdir()
    (tests / "test_suite.py").write_text(SUITE)
    monkeypatch.chdir(tmp_path)
    return tmp_path


def test_report_discovers_from_testpaths(project, capsys, monkeypatch) -> None:
    monkeypatch.setattr("sys.argv", ["testmap", "report"])
    main()
    out = capsys.readouterr().out
    assert "parser" in out
    # parser has unit but not integration -> flagged as missing.
    assert "parser: integration" in out


def test_report_ingests_json_file(project, capsys, monkeypatch) -> None:
    records = {"tests": [{"feature": "parser", "kind": "integration"}]}
    (project / "in.json").write_text(json.dumps(records))
    monkeypatch.setattr("sys.argv", ["testmap", "report", "in.json"])
    main()
    out = capsys.readouterr().out
    assert "parser: unit" in out  # the JSON, not the discovered source, drove this
