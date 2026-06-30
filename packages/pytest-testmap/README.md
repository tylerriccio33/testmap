# pytest-testmap

Pytest plugin for testmap. Provides the `@testmap(feature=..., kind=...)`
decorator, collects annotated tests during a run, and exposes `--testmap`
(terminal matrix) and `--testmap-json PATH` (machine-readable report).
