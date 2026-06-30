"""Core of testmap: load config, aggregate test records, render the report.

The same renderer is used by the standalone CLI and by the pytest plugin, so the
terminal output is identical no matter how the metadata was produced.
"""

import tomllib
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Config:
    """The kind taxonomy and which kinds each feature must have."""

    kinds: list[str]
    required: list[str]  # global default required kinds
    features: dict[str, list[str]]  # per-feature required-kind overrides

    def required_for(self, feature: str) -> list[str]:
        return self.features.get(feature, self.required)


def load_config(pyproject: Path) -> Config:
    """Load `[tool.testmap]` from a pyproject.toml.

    Invariant: every required kind (global and per-feature) is one of `kinds`;
    a stray kind is a config bug, so we raise rather than silently drop it.
    """
    tool = tomllib.loads(pyproject.read_text(encoding="utf-8")).get("tool", {})
    if "testmap" not in tool:
        raise ValueError(f"no [tool.testmap] configuration in {pyproject}")
    data = tool["testmap"]
    kinds: list[str] = data["kinds"]
    required: list[str] = data.get("required", kinds)
    features: dict[str, list[str]] = data.get("features", {})
    for name, req in {"required": required, **features}.items():
        unknown = sorted(set(req) - set(kinds))
        if unknown:
            raise ValueError(f"[tool.testmap] {name} references unknown kinds {unknown}")
    return Config(kinds=kinds, required=required, features=features)


def build_report(tests: list[dict[str, str]], config: Config) -> dict:
    """Aggregate `{feature, kind}` records into the feature x kind matrix.

    Raises on a kind not declared in `config.kinds` (no silent fallback). Only
    features with at least one test appear; a feature is complete when none of
    its required kinds are missing.
    """
    matrix: dict[str, dict[str, int]] = {}
    for test in tests:
        feature, kind = test["feature"], test["kind"]
        if kind not in config.kinds:
            raise ValueError(f"unknown test kind {kind!r} (declared kinds: {config.kinds})")
        matrix.setdefault(feature, {k: 0 for k in config.kinds})[kind] += 1

    features = {}
    for feature in sorted(matrix):
        counts = matrix[feature]
        missing = [k for k in config.required_for(feature) if counts[k] == 0]
        features[feature] = {"counts": counts, "missing": missing, "complete": not missing}
    return {"features": features}


def render(report: dict, config: Config) -> str:
    """Render the report as the feature x kind table plus the Missing section."""
    headers = ["Feature", *(k.capitalize() for k in config.kinds), "Status"]
    rows = [headers]
    for feature, data in report["features"].items():
        status = "✓" if data["complete"] else "✗"
        rows.append([feature, *(str(data["counts"][k]) for k in config.kinds), status])

    widths = [max(len(row[i]) for row in rows) for i in range(len(headers))]

    def fmt(cells: list[str]) -> str:
        # Feature left-justified; counts and status right-justified for a clean grid.
        return "  ".join(
            [cells[0].ljust(widths[0])] + [c.rjust(widths[i]) for i, c in enumerate(cells[1:], 1)]
        )

    lines = [fmt(headers), "-" * len(fmt(headers)), *(fmt(row) for row in rows[1:])]

    missing = [
        f"  • {feature}: {kind}"
        for feature, data in report["features"].items()
        for kind in data["missing"]
    ]
    if missing:
        lines += ["", "Missing:", *missing]
    return "\n".join(lines)
