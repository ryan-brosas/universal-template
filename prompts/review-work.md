---
description: Review the current changes for defects
argument-hint: "[scope]"
---
Review the current changes for bugs, regressions, and unnecessary complexity.
Use Sourcebot's ask_codebase tool to inspect the indexed baseline of the
affected code and how comparable implementations handle the same concern, so
findings are grounded beyond the diff. Inspect the important evidence yourself
rather than restating the implementation summary. Focus on actionable findings,
show where they occur, and explain why they matter. Don't edit anything; Code Ask
is indexed retrieval, not an external review of the working-tree patch.

${ARGUMENTS:-}
