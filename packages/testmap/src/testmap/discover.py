"""Discover `@testmap`-tagged tests by scanning source, no pytest required.

The pytest plugin collects the same `{feature, kind}` records at collection time.
This module reads them statically instead: it parses each Python file and pulls
the `feature`/`kind` arguments off every `@testmap(...)` (or
`@pytest.mark.testmap(...)`) decorator, so `testmap report` can build the matrix
straight from the codebase.
"""

import ast
import os
from collections.abc import Iterable
from pathlib import Path


def _string_arg(call: ast.Call, name: str) -> str | None:
    for kw in call.keywords:
        if kw.arg == name and isinstance(kw.value, ast.Constant):
            value = kw.value.value
            if isinstance(value, str):
                return value
    return None


def _is_testmap_decorator(node: ast.expr) -> ast.Call | None:
    """Return the decorator Call if it targets a `testmap` marker, else None."""
    if not isinstance(node, ast.Call):
        return None
    func = node.func
    # `@testmap(...)` (bare import) or `@pytest.mark.testmap(...)` / `@x.testmap(...)`.
    if isinstance(func, ast.Name) and func.id == "testmap":
        return node
    if isinstance(func, ast.Attribute) and func.attr == "testmap":
        return node
    return None


def _records_from_file(path: Path, root: Path) -> list[dict[str, str]]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except SyntaxError, UnicodeDecodeError:
        return []  # not parseable Python; nothing to collect

    records: list[dict[str, str]] = []
    rel = os.path.relpath(path, root)
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            continue
        for decorator in node.decorator_list:
            call = _is_testmap_decorator(decorator)
            if call is None:
                continue
            feature = _string_arg(call, "feature")
            kind = _string_arg(call, "kind")
            if feature is None or kind is None:
                raise ValueError(f"{rel}::{node.name}: @testmap requires string feature and kind")
            records.append({"nodeid": f"{rel}::{node.name}", "feature": feature, "kind": kind})
    return records


def discover(paths: Iterable[Path], root: Path | None = None) -> list[dict[str, str]]:
    """Scan `paths` (files or directories) for `@testmap`-tagged tests.

    `root` anchors the reported nodeids (defaults to the current directory).
    Records are sorted by nodeid so the output is stable across runs.
    """
    root = (root or Path.cwd()).resolve()
    records: list[dict[str, str]] = []
    for path in paths:
        files = sorted(path.rglob("*.py")) if path.is_dir() else [path]
        for file in files:
            records.extend(_records_from_file(file, root))
    return sorted(records, key=lambda r: r["nodeid"])
