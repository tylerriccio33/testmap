"""`testmap report` — render the matrix, discovering tagged tests or ingesting JSON."""

import argparse
import json
import tomllib
from pathlib import Path

from testmap.discover import discover
from testmap.report import build_report, load_config, render


def _default_paths(pyproject: Path) -> list[Path]:
    """Testpaths from `[tool.pytest.ini_options]`, falling back to the cwd."""
    if pyproject.is_file():
        ini = tomllib.loads(pyproject.read_text(encoding="utf-8"))
        testpaths = ini.get("tool", {}).get("pytest", {}).get("ini_options", {}).get("testpaths")
        if testpaths:
            return [Path(p) for p in testpaths]
    return [Path(".")]


def _load_records(path: Path | None, config_path: Path) -> list[dict[str, str]]:
    """A JSON file is ingested as-is; a directory (or nothing) is scanned for @testmap."""
    if path is not None and path.is_file() and path.suffix == ".json":
        return json.loads(path.read_text(encoding="utf-8"))["tests"]
    paths = [path] if path is not None else _default_paths(config_path)
    return discover(paths)


def main() -> None:
    parser = argparse.ArgumentParser(prog="testmap")
    sub = parser.add_subparsers(dest="command", required=True)
    report = sub.add_parser("report", help="render a testmap report from source or a JSON file")
    report.add_argument(
        "path",
        type=Path,
        nargs="?",
        help="a JSON file emitted by --testmap-json, or a dir to scan "
        "(default: scan testpaths from pyproject.toml)",
    )
    report.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    report.add_argument(
        "--config",
        type=Path,
        default=Path("pyproject.toml"),
        help="pyproject.toml holding [tool.testmap] (default: ./pyproject.toml)",
    )
    args = parser.parse_args()

    config = load_config(args.config)
    tests = _load_records(args.path, args.config)
    result = build_report(tests, config)
    print(json.dumps(result, indent=2) if args.json else render(result, config))
