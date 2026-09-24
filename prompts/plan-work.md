---
description: Plan the work before changing anything
argument-hint: "[request]"
---
Help me plan the work we've discussed. Ground the plan in the current project.
Read known or current files directly and verify decision-critical findings
against the working tree. When a broad unresolved codebase question would change
the plan, use Sourcebot's ask_codebase tool, following the cross-repository
source procedure, to trace the relevant flow, identify tests and likely change
points, and compare indexed implementations; keep known local questions direct,
and skip indexed research for design-only work such as Figma assets, components
and tokens. Honor an explicit request for that tool. If Sourcebot is unavailable
or unhelpful for a question that genuinely needs it, say so and continue locally
rather than implying the lane ran. Explain the important tradeoffs, include how
we'll know it works, and keep the plan in this conversation; don't make changes
yet.

${ARGUMENTS:-}
