import pytest
from testmap.report import Config, build_report, load_config, render

CONFIG = Config(
    kinds=["unit", "integration", "property", "perf"],
    required=["unit", "integration"],
    features={"processor": ["unit", "integration", "property"]},
)

TESTS = [
    {"feature": "processor", "kind": "unit"},
    {"feature": "processor", "kind": "unit"},
    {"feature": "processor", "kind": "integration"},
    {"feature": "parser", "kind": "unit"},
    {"feature": "parser", "kind": "integration"},
]


def test_build_report_counts_and_missing() -> None:
    report = build_report(TESTS, CONFIG)["features"]
    assert report["processor"]["counts"] == {"unit": 2, "integration": 1, "property": 0, "perf": 0}
    # processor overrides required to include property, which it lacks.
    assert report["processor"]["missing"] == ["property"]
    assert report["processor"]["complete"] is False
    # parser uses the global required (unit + integration), both present.
    assert report["parser"]["missing"] == []
    assert report["parser"]["complete"] is True


def test_build_report_rejects_unknown_kind() -> None:
    with pytest.raises(ValueError, match="unknown test kind 'fuzz'"):
        build_report([{"feature": "x", "kind": "fuzz"}], CONFIG)


def test_render_contains_table_and_missing() -> None:
    out = render(build_report(TESTS, CONFIG), CONFIG)
    assert "Feature" in out and "Status" in out
    assert "processor" in out and "parser" in out
    assert "Missing:" in out
    assert "  • processor: property" in out


def test_load_config(tmp_path) -> None:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        '[tool.testmap]\nkinds = ["unit", "integration"]\n'
        '[tool.testmap.features]\nsender = ["unit"]\n'
    )
    config = load_config(pyproject)
    assert config.kinds == ["unit", "integration"]
    # required defaults to kinds when unspecified.
    assert config.required == ["unit", "integration"]
    assert config.required_for("sender") == ["unit"]


def test_load_config_rejects_unknown_required_kind(tmp_path) -> None:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[tool.testmap]\nkinds = ["unit"]\nrequired = ["unit", "perf"]\n')
    with pytest.raises(ValueError, match="unknown kinds"):
        load_config(pyproject)
