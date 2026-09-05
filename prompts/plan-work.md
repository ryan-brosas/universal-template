# Plan the requested work

Create an implementation-ready plan for the request below in this conversation without modifying files, external state, or history. Do not create or propose a repository planning artifact merely because the user asks for a plan. If recovery or coordination may require a durable record, explicitly load `goal-setup` from the installed skill catalog; duration alone is not a reason to create one.

Treat the requested outcome or concern as intent, not a predetermined implementation. Optimize for a plan that increases correctness, feasibility, clarity, and maintainability while reducing unnecessary complexity, risk, churn, and maintenance cost. Do not simplify one dimension by shifting material cost into another.

Ground the plan in the current source, instructions, tests, and configuration. Use your judgment to choose the design and level of detail. State genuine boundaries, acceptance conditions, likely change points, and decisive verification without adding ceremony that does not help execution.

## Reusable context

- Current project behavior is ground truth to consult before proposing; do not plan from memory of a design doc.
- Distinguish what is verified (command output, tests, source) from what is assumed in scoping and estimates.
- Choose the smallest change that satisfies the need; plan the removal of dead or duplicated paths, not new layers.
- Reuse existing checks for objective properties. Propose a new gate only when the failure it prevents justifies its maintenance cost.

Request:
$ARGUMENTS
