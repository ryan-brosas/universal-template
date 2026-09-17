---
description: Verify the current work actually works
argument-hint: "[scope]"
---
Check whether the current work meets what we asked for. Challenge the chosen
approach against current source and the actual patch, not only the plan summary.
When correctness depends on code structure, callers or comparable
implementations, use Sourcebot's ask_codebase tool to challenge the approach
against the indexed baseline; documentation- and design-only work needs direct
evidence instead. Reuse a valid brief rather than repeating a call per phase, and
honor an explicit request for that tool. If Sourcebot is unavailable or unhelpful
for a question that genuinely needs it, say so and rely on local execution
without implying indexed corroboration. Execution, not the index,
proves the local patch. Run the relevant checks and tell me what passed, what
failed, and what remains untested. Never report a test as passed unless it was
executed. Don't apply fixes or change external state unless I've asked you to.

${ARGUMENTS:-}
