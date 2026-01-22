---
description: "Use when generating or editing Python tests in this repository"
applyTo: "**/*.py"
---
When creating or updating tests for this repository:

- Use `pytest` assertions and `pytest.raises` for exception checks.
- Follow existing naming conventions: test classes named `*Tests` and methods/functions named `test_*`.
- Prefer deterministic tests with explicit fixtures/input setup; avoid timing-sensitive logic.
- Keep tests focused on behavior, not implementation details.
- Minimize mocking; use it only to isolate real external effects.
- For YAML/config tests, prefer path-based test data under `tests/config/data/` when relevant.
- Add coverage for happy path, edge cases, and error paths.
- If behavior is unclear, document assumptions in the test body or in a short note accompanying generated tests.
