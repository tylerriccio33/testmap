"""`testmap report <file.json>` — render a report from plugin-emitted metadata."""

import argparse
import json
from pathlib import Path

from testmap.report import build_report, load_config, render


def main() -> None:
    parser = argparse.ArgumentParser(prog="testmap")
    sub = parser.add_subparsers(dest="command", required=True)
    report = sub.add_parser("report", help="render a testmap report from a JSON file")
    report.add_argument("path", type=Path, help="testmap JSON emitted by --testmap-json")
    report.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    report.add_argument(
        "--config",
        type=Path,
        default=Path("pyproject.toml"),
        help="pyproject.toml holding [tool.testmap] (default: ./pyproject.toml)",
    )
    args = parser.parse_args()

    config = load_config(args.config)
    tests = json.loads(args.path.read_text(encoding="utf-8"))["tests"]
    result = build_report(tests, config)
    print(json.dumps(result, indent=2) if args.json else render(result, config))
