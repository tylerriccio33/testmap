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


def test_testmap_only_renders_without_running(pytester) -> None:
    pytester.makepyfile(
        """
        from pytest_testmap import testmap

        @testmap(feature="parser", kind="unit")
        def test_a(): pass
        """
    )
    (pytester.path / "pyproject.toml").write_text(PYPROJECT)

    result = pytester.runpytest("--testmap-only")
    # No tests execute, but the matrix still renders.
    result.assert_outcomes()
    result.stdout.fnmatch_lines(["*testmap*", "*parser*"])


def test_no_testmap_option_is_inert(pytester) -> None:
    # Without any --testmap flag the plugin collects nothing and prints no matrix.
    pytester.makepyfile(
        """
        from pytest_testmap import testmap

        @testmap(feature="parser", kind="unit")
        def test_a(): pass
        """
    )
    (pytester.path / "pyproject.toml").write_text(PYPROJECT)

    result = pytester.runpytest()
    result.assert_outcomes(passed=1)
    # The matrix is never rendered, so its header column is absent.
    assert "Feature" not in result.stdout.str()


def test_untagged_tests_are_skipped(pytester) -> None:
    # A test without a @testmap marker is ignored while tagged ones are collected.
    pytester.makepyfile(
        """
        from pytest_testmap import testmap

        @testmap(feature="parser", kind="unit")
        def test_a(): pass

        def test_untagged(): pass
        """
    )
    (pytester.path / "pyproject.toml").write_text(PYPROJECT)
    out = pytester.path / "out.json"

    result = pytester.runpytest("--testmap", f"--testmap-json={out}")
    result.assert_outcomes(passed=2)
    records = json.loads(out.read_text())["tests"]
    assert {(r["feature"], r["kind"]) for r in records} == {("parser", "unit")}


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
