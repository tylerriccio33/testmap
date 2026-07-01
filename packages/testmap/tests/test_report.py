import pytest
from testmap.report import Config, build_report, load_config, render

CONFIG = Config(
    kinds=["unit", "integration", "property", "perf"],
    required=["unit", "integration"],
    features={"processor": ["unit", "integration", "property"]},
    excludes={},
    statuses={"complete": "✓", "incomplete": "✗"},
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
    # statuses default when unspecified.
    assert config.statuses == {"complete": "✓", "incomplete": "✗"}


def test_load_config_custom_statuses(tmp_path) -> None:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        '[tool.testmap]\nkinds = ["unit"]\n'
        '[tool.testmap.statuses]\ncomplete = "PASS"\nincomplete = "TODO"\n'
    )
    config = load_config(pyproject)
    assert config.statuses == {"complete": "PASS", "incomplete": "TODO"}
    out = render(build_report([{"feature": "a", "kind": "unit"}], config), config)
    assert "PASS" in out and "TODO" not in out


def test_load_config_partial_statuses_keeps_default(tmp_path) -> None:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        '[tool.testmap]\nkinds = ["unit"]\n[tool.testmap.statuses]\nincomplete = "!"\n'
    )
    config = load_config(pyproject)
    assert config.statuses == {"complete": "✓", "incomplete": "!"}


def test_load_config_rejects_unknown_status(tmp_path) -> None:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[tool.testmap]\nkinds = ["unit"]\n[tool.testmap.statuses]\nflaky = "?"\n')
    with pytest.raises(ValueError, match="unknown states"):
        load_config(pyproject)


def test_load_config_rejects_unknown_required_kind(tmp_path) -> None:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[tool.testmap]\nkinds = ["unit"]\nrequired = ["unit", "perf"]\n')
    with pytest.raises(ValueError, match="unknown kinds"):
        load_config(pyproject)


def test_load_config_feature_exclude(tmp_path) -> None:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        '[tool.testmap]\nkinds = ["unit", "integration", "perf"]\n'
        'required = ["unit", "integration", "perf"]\n'
        '[tool.testmap.features]\nauth = { exclude = ["perf"] }\n'
    )
    config = load_config(pyproject)
    # perf is dropped from auth's requirements; other features keep it.
    assert config.required_for("auth") == ["unit", "integration"]
    assert config.excluded_for("auth") == ["perf"]
    assert config.required_for("other") == ["unit", "integration", "perf"]


def test_exclude_makes_feature_complete_and_renders_na() -> None:
    config = Config(
        kinds=["unit", "integration", "perf"],
        required=["unit", "integration", "perf"],
        features={},
        excludes={"auth": ["perf"]},
        statuses={"complete": "✓", "incomplete": "✗"},
    )
    tests = [{"feature": "auth", "kind": "unit"}, {"feature": "auth", "kind": "integration"}]
    report = build_report(tests, config)
    # No perf test, but perf is excluded, so auth is complete with nothing missing.
    assert report["features"]["auth"]["complete"] is True
    assert report["features"]["auth"]["missing"] == []
    out = render(report, config)
    assert "n/a" in out
    assert "Missing:" not in out


def test_load_config_rejects_unknown_excluded_kind(tmp_path) -> None:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        '[tool.testmap]\nkinds = ["unit"]\n[tool.testmap.features]\nauth = { exclude = ["perf"] }\n'
    )
    with pytest.raises(ValueError, match="unknown kinds"):
        load_config(pyproject)
