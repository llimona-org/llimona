---
description: "Explain selected code clearly with concrete file and line references"
name: "Explain With Paths"
argument-hint: "Optional focus (e.g., control flow, error handling, data model, performance)"
agent: "agent"
---
Explain the code I selected with precise repository references.

Inputs to use:
- Current editor selection first.
- Current file path.
- Related code paths required to explain dependencies and call flow.
- Optional user argument as the explanation focus.

Requirements:
- Start with a concise summary of purpose.
- Explain behavior in execution order.
- Include concrete file references for every non-trivial claim.
- Use paths with optional line numbers like `src/module.py:42`.
- Point out assumptions, edge cases, and likely failure modes.

Output format:
1. "Purpose" (2-4 sentences).
2. "How It Works" (short numbered list).
3. "Key References" (path-based bullets).
4. "Risks/Notes" (short bullets).

Style:
- Keep wording direct and technical.
- Avoid generic descriptions not grounded in the actual code.
