---
description: Review the current changes for defects
argument-hint: "[scope]"
---
Review the current changes for bugs, regressions, and unnecessary complexity.
Use Sourcebot's ask_codebase tool during review to inspect the indexed baseline
of the affected code and how comparable implementations handle the same concern.
Reuse the session brief only when it covers the final patch; otherwise ask a
bounded review follow-up. If Sourcebot is unavailable or no relevant repository
is indexed, say so and review local source without implying indexed coverage.
Inspect the important evidence yourself rather than restating the implementation
summary. Focus on actionable findings, show where they occur, and explain why
they matter. Don't edit anything; Code Ask is indexed retrieval, not an external
review of the working-tree patch.

${ARGUMENTS:-}
