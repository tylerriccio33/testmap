import json

PYPROJECT = (
    "[tool.pytest.ini_options]\n"
    "[tool.testmap]\n"
    'kinds = ["unit", "integration", "property", "perf"]\n'
    'required = ["unit", "integration"]\n'
)


def test_matrix_and_json(pytester) -> None:
    pytester.makepyfile(
        """
        from pytest_testmap import testmap

        @testmap(feature="processor", kind="unit")
        def test_a(): pass

        @testmap(feature="processor", kind="integration")
        def test_b(): pass

        @testmap(feature="parser", kind="unit")
        def test_c(): pass
        """
    )
    (pytester.path / "pyproject.toml").write_text(PYPROJECT)
    out = pytester.path / "out.json"

    result = pytester.runpytest("--testmap", f"--testmap-json={out}")
    result.assert_outcomes(passed=3)
    # processor has unit + integration (complete); parser is missing integration.
    result.stdout.fnmatch_lines(["*testmap*", "*processor*", "*Missing:*", "*parser: integration*"])

    records = json.loads(out.read_text())["tests"]
    assert {(r["feature"], r["kind"]) for r in records} == {
        ("processor", "unit"),
        ("processor", "integration"),
        ("parser", "unit"),
    }


def test_marker_without_feature_or_kind_errors(pytester) -> None:
    pytester.makepyfile(
        """
        import pytest

        @pytest.mark.testmap
        def test_a(): pass
        """
    )
    (pytester.path / "pyproject.toml").write_text(PYPROJECT)

    result = pytester.runpytest("--testmap")
    result.stderr.fnmatch_lines(["*requires feature and kind*"])
