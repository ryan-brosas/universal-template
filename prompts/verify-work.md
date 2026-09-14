---
description: Verify the current work actually works
argument-hint: "[scope]"
---
Check whether the current work meets what we asked for. Challenge the chosen
approach against current source and the actual patch, not only the plan summary.
Use Sourcebot's ask_codebase tool during verification to challenge the approach
against the indexed baseline of the affected code and comparable
implementations. Reuse the session brief only when it covers the final decision
surface; otherwise ask a bounded verification follow-up. If Sourcebot is
unavailable or no relevant repository is indexed, say so and rely on local
execution without implying indexed corroboration. The local patch itself is
proven by execution. Run the relevant checks and tell me what passed, what
failed, and what remains untested. Never report a test as passed unless it was
executed. Don't apply fixes or change external state unless I've asked you to.

${ARGUMENTS:-}
