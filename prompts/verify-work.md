---
description: Verify the current work actually works
argument-hint: "[scope]"
---
Check whether the current work meets what we asked for. Challenge the chosen
approach against current source and the actual patch, not only the plan summary.
Use Sourcebot's ask_codebase tool to challenge the approach against the indexed
baseline of the affected code and comparable implementations; the local patch
itself is proven by execution. Run the relevant checks and tell me what passed,
what failed, and what remains untested. Never report a test as passed unless it
was executed. Don't apply fixes or change external state unless I've asked you
to.

${ARGUMENTS:-}
