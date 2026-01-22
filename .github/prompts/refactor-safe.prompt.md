---
description: "Refactor selected code safely with behavior-preserving constraints"
name: "Refactor Safe"
argument-hint: "Optional goal (e.g., reduce duplication, improve readability, split function)"
agent: "agent"
---
Refactor the code I selected with a strict safety-first approach.

Inputs to use:
- Current editor selection as the primary target.
- Current file path and file type.
- Nearby project context needed to keep behavior and style consistent.
- Optional user argument as the refactor objective.

Process:
- Identify current behavior and invariants before proposing edits.
- Prefer small, local changes over broad rewrites.
- Preserve public interfaces unless explicitly asked to change them.
- Keep error handling behavior and side effects equivalent.
- If uncertainty exists, choose the lower-risk option and call it out.

Output format:
1. "Refactor Plan" (3-6 bullets).
2. "Risk Check" with potential regressions and mitigations.
3. Proposed code edits in fenced code block(s).
4. "Validation" with concrete tests/checks to run.

Constraints:
- Do not alter unrelated files.
- Do not change functionality unless explicitly requested.
- Match repository formatting and naming conventions.
