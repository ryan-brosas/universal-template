---
description: Implement the agreed work end to end
argument-hint: "[request]"
---
Implement what we've agreed on, end to end. Keep the solution simple and
preserve unrelated work. Use Sourcebot's ask_codebase tool when a broad unresolved
codebase question would change the implementation, such as tracing callers,
confirming semantics or comparing indexed implementations; reuse a valid brief,
and skip it when a known local file or the current patch settles the question.
Figma/Paper-only work stays with live design evidence. If relevant or explicitly
requested Sourcebot research is unavailable, say so rather than pretending the
lane ran. The working tree and actual patch are authoritative; verify
decision-critical findings against them. Tell me what changed and anything still
unresolved.

${ARGUMENTS:-}
