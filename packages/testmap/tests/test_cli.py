import json
import runpy
from pathlib import Path

import pytest
from testmap.cli import _default_paths, main

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


def test_module_entrypoint_runs_cli(project, capsys, monkeypatch) -> None:
    # `python -m testmap` dispatches to the CLI (exercises __main__.py).
    monkeypatch.setattr("sys.argv", ["testmap", "report"])
    runpy.run_module("testmap", run_name="__main__")
    assert "parser" in capsys.readouterr().out


def test_default_paths_falls_back_to_cwd(tmp_path) -> None:
    # No [tool.pytest.ini_options] testpaths -> scan the current directory.
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[tool.testmap]\nkinds = ["unit"]\n')
    assert _default_paths(pyproject) == [Path(".")]


def test_default_paths_missing_pyproject(tmp_path) -> None:
    # A pyproject that doesn't exist also falls back to the cwd.
    assert _default_paths(tmp_path / "nope.toml") == [Path(".")]


def test_report_ingests_json_file(project, capsys, monkeypatch) -> None:
    records = {"tests": [{"feature": "parser", "kind": "integration"}]}
    (project / "in.json").write_text(json.dumps(records))
    monkeypatch.setattr("sys.argv", ["testmap", "report", "in.json"])
    main()
    out = capsys.readouterr().out
    assert "parser: unit" in out  # the JSON, not the discovered source, drove this
