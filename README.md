# testmap

testmap answers a question code-coverage tools can't: **what validation evidence
do we have?** For each *feature* of your codebase it builds a matrix of how many
*unit / integration / property / perf* tests exist, and flags the required kinds
that are missing — useful for humans and for agents ("generate property tests for
`processor`").

```
Feature      Unit  Integration  Property  Perf
----------------------------------------------
processor      12       4           0      ✗
sender          8       0           0      ✗
parser         19       7           5      ✓

Missing:
  • sender: integration
  • processor: property
```

## Packages

This is a [uv workspace](https://docs.astral.sh/uv/concepts/projects/workspaces/)
monorepo with two distributions:

- **`testmap`** (`packages/testmap`) — standalone core + CLI. Ingests test
  metadata and renders the matrix / missing report.
- **`pytest-testmap`** (`packages/pytest-testmap`) — pytest plugin. Provides the
  `@testmap(feature=..., kind=...)` decorator and the `--testmap` /
  `--testmap-json` options.

## Configuration

The kind taxonomy and required kinds live under `[tool.testmap]` in `pyproject.toml`:

```toml
[tool.testmap]
kinds = ["unit", "integration", "property", "perf"]
required = ["unit", "integration"]   # global default

[tool.testmap.features]
processor = ["unit", "integration", "property"]   # per-feature override
```

## Development

```bash
uv sync          # set up the workspace venv
make lint        # ruff format + ruff check + pyrefly
make test        # pytest with coverage
```

Commits follow [Conventional Commits](https://www.conventionalcommits.org).
Install the git hooks (lint, type-check, commit-message check) with
[`prek`](https://github.com/j178/prek):

```bash
prek install --hook-type pre-commit --hook-type commit-msg
```
