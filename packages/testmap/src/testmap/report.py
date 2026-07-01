"""Core of testmap: load config, aggregate test records, render the report.

The same renderer is used by the standalone CLI and by the pytest plugin, so the
terminal output is identical no matter how the metadata was produced.
"""

import tomllib
from dataclasses import dataclass
from pathlib import Path

# The Status column symbols, used when [tool.testmap.statuses] is absent. At
# least one of each state so the table renders without any config.
DEFAULT_STATUSES = {"complete": "✓", "incomplete": "✗"}


@dataclass(frozen=True)
class Config:
    """The kind taxonomy and which kinds each feature must have."""

    kinds: list[str]
    required: list[str]  # global default required kinds
    features: dict[str, list[str]]  # per-feature required-kind overrides
    excludes: dict[str, list[str]]  # per-feature kinds dropped from requirements
    statuses: dict[str, str]  # Status-column symbol per state (complete/incomplete)

    def excluded_for(self, feature: str) -> list[str]:
        return self.excludes.get(feature, [])

    def required_for(self, feature: str) -> list[str]:
        # Start from the feature's override (or the global default), then drop
        # any kinds this feature opts out of, e.g. a feature that needs no perf.
        base = self.features.get(feature, self.required)
        excluded = self.excludes.get(feature, ())
        return [k for k in base if k not in excluded]

    def status_symbol(self, complete: bool) -> str:
        return self.statuses["complete" if complete else "incomplete"]


def load_config(pyproject: Path) -> Config:
    """Load `[tool.testmap]` from a pyproject.toml.

    A `[tool.testmap.features]` entry is either a list (the required kinds for
    that feature) or a table taking `required` and/or `exclude`; excluded kinds
    are dropped from that feature's requirements.

    Invariant: every referenced kind (global, per-feature, excluded) is one of
    `kinds`; a stray kind is a config bug, so we raise rather than silently drop it.
    """
    tool = tomllib.loads(pyproject.read_text(encoding="utf-8")).get("tool", {})
    if "testmap" not in tool:
        raise ValueError(f"no [tool.testmap] configuration in {pyproject}")
    data = tool["testmap"]
    kinds: list[str] = data["kinds"]
    required: list[str] = data.get("required", kinds)

    features: dict[str, list[str]] = {}
    excludes: dict[str, list[str]] = {}
    for name, entry in data.get("features", {}).items():
        if isinstance(entry, dict):
            if "required" in entry:
                features[name] = entry["required"]
            if entry.get("exclude"):
                excludes[name] = entry["exclude"]
        else:
            features[name] = entry

    referenced = {"required": required, **features, **excludes}
    for name, kind_list in referenced.items():
        unknown = sorted(set(kind_list) - set(kinds))
        if unknown:
            raise ValueError(f"[tool.testmap] {name} references unknown kinds {unknown}")
    # Merge configured status symbols over the defaults so a partial table (e.g.
    # only overriding "complete") keeps a symbol for the other state.
    statuses = {**DEFAULT_STATUSES, **data.get("statuses", {})}
    unknown_states = sorted(set(statuses) - set(DEFAULT_STATUSES))
    if unknown_states:
        raise ValueError(
            f"[tool.testmap.statuses] unknown states {unknown_states} "
            f"(valid: {sorted(DEFAULT_STATUSES)})"
        )
    return Config(
        kinds=kinds, required=required, features=features, excludes=excludes, statuses=statuses
    )


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
        excluded = [k for k in config.kinds if k in config.excluded_for(feature)]
        features[feature] = {
            "counts": counts,
            "missing": missing,
            "excluded": excluded,
            "complete": not missing,
        }
    return {"features": features}


def render(report: dict, config: Config) -> str:
    """Render the report as the feature x kind table plus the Missing section."""
    headers = ["Feature", *(k.capitalize() for k in config.kinds), "Status"]
    rows = [headers]
    for feature, data in report["features"].items():
        status = config.status_symbol(data["complete"])
        # Excluded kinds render as n/a so a blank isn't mistaken for a gap.
        cells = ["n/a" if k in data["excluded"] else str(data["counts"][k]) for k in config.kinds]
        rows.append([feature, *cells, status])

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
