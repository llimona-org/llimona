---
description: "Generate high-value tests from selected code with repo-aligned style"
name: "Smart Review"
argument-hint: "Optional focus (e.g., edge cases, async behavior, error handling)"
agent: "agent"
---
Generate tests for the code I selected.

Inputs to use:
- The current editor selection as the primary source of truth.
- The current file path and file type to match language and testing conventions.
- Related repository context (existing tests, fixtures, helpers, and test style) before writing output.
- Optional user argument as a focus area.

Requirements:
- Follow existing test patterns and naming conventions in this repository.
- Default to `pytest` style unless the repository clearly uses another framework.
- Cover happy path, edge cases, and error paths.
- Prefer deterministic tests; avoid flaky timing assumptions.
- Minimize mocking unless external side effects require it.
- If behavior is unclear, state assumptions explicitly.

Output format:
1. A short "Coverage Plan" list (3-7 bullets).
2. "Placement" notes indicating target test file path(s) and whether to create or edit.
3. The proposed test code in a single fenced code block.
4. A short "Gaps/Assumptions" list.

Quality bar:
- Tests should be runnable with the project's current test tooling.
- Use clear, behavior-focused test names.
- Do not modify production code unless explicitly requested.
