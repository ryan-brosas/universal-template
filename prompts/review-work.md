---
description: Review the current changes for defects
argument-hint: "[scope]"
---
Review the current changes for bugs, regressions, and unnecessary complexity.
When a code change needs indexed baseline context or comparable implementations,
use Sourcebot's ask_codebase tool for that question; reuse a valid brief, and rely
on direct source for narrow or design-only changes instead of repeating a call
per review. Honor an explicit request for that tool. If Sourcebot is unavailable
or unhelpful for a question that genuinely needs it, say so and review local
source without implying indexed coverage.
Inspect the important evidence yourself rather than restating the implementation
summary. Focus on actionable findings, show where they occur, and explain why
they matter. Don't edit anything; Code Ask is indexed retrieval, not an external
review of the working-tree patch.

${ARGUMENTS:-}
