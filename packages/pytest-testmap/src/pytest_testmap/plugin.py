"""Pytest plugin: collect `@testmap`-tagged tests and report the matrix.

`--testmap` prints the feature x kind matrix (rendered by testmap's core, so the
output matches the standalone CLI). `--testmap-json PATH` writes the raw records;
the standalone `testmap` tool ingests that file and applies the config later.
"""

import json
from pathlib import Path

import pytest
from testmap.report import build_report, load_config, render

# Records collected during the run, stashed on the pytest config.
_RECORDS = pytest.StashKey[list[dict[str, str]]]()


def pytest_addoption(parser: pytest.Parser) -> None:
    group = parser.getgroup("testmap")
    group.addoption(
        "--testmap", action="store_true", help="print the testmap feature x kind matrix"
    )
    group.addoption(
        "--testmap-only",
        action="store_true",
        help="print the matrix without running any tests",
    )
    group.addoption(
        "--testmap-json", metavar="PATH", help="write the testmap report as JSON to PATH"
    )


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers", "testmap(feature, kind): tag a test with its feature and kind"
    )


@pytest.hookimpl(tryfirst=True)
def pytest_runtestloop(session: pytest.Session) -> bool | None:
    # `--testmap-only` renders the report from collected metadata; skip execution.
    if session.config.option.testmap_only:
        return True
    return None


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    if not (config.option.testmap or config.option.testmap_only or config.option.testmap_json):
        return
    records = []
    for item in items:
        marker = item.get_closest_marker("testmap")
        if marker is None:
            continue
        try:
            records.append(
                {
                    "nodeid": item.nodeid,
                    "feature": marker.kwargs["feature"],
                    "kind": marker.kwargs["kind"],
                }
            )
        except KeyError as e:
            raise pytest.UsageError(f"{item.nodeid}: @testmap requires feature and kind") from e
    config.stash[_RECORDS] = records


def pytest_terminal_summary(terminalreporter, exitstatus: int, config: pytest.Config) -> None:
    records = config.stash.get(_RECORDS, None)
    if records is None:  # neither option was active this run
        return
    if config.option.testmap_json:
        Path(config.option.testmap_json).write_text(
            json.dumps({"tests": records}, indent=2), encoding="utf-8"
        )
    if config.option.testmap or config.option.testmap_only:
        cfg = load_config(config.rootpath / "pyproject.toml")
        terminalreporter.section("testmap")
        terminalreporter.write_line(render(build_report(records, cfg), cfg))
