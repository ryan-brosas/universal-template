---
description: Plan the work before changing anything
argument-hint: "[request]"
---
Help me plan the work we've discussed. Ground the plan in the current project.
For non-trivial code work, use Sourcebot's ask_codebase tool during planning to
trace the relevant flow, identify tests and likely change points, and compare
indexed implementations where useful. Read known or current files directly and
verify decision-critical findings against the working tree. Explain the
important tradeoffs, include how we'll know it works, and keep the plan in this
conversation; don't make changes yet.

${ARGUMENTS:-}
