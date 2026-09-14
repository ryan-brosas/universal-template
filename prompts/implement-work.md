---
description: Implement the agreed work end to end
argument-hint: "[request]"
---
Implement what we've agreed on, end to end. Keep the solution simple and
preserve unrelated work. Use Sourcebot's ask_codebase tool during implementation
to trace callers, confirm semantics, and compare indexed implementations before
committing to a pattern. Reuse the session brief when it still covers the
decision; ask a bounded follow-up when implementation changes the affected flow.
If Sourcebot is unavailable or no relevant repository is indexed, say so rather
than pretending the lane ran. The working tree and actual patch are
authoritative; verify decision-critical findings against them. Tell me what
changed and anything still unresolved.

${ARGUMENTS:-}
