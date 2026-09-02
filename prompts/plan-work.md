# Plan the requested work

Create an implementation-ready plan for the request below in this conversation without modifying files, external state, or history. Do not create or propose a repository planning artifact merely because the user asks for a plan. A durable post-code work record is appropriate only when the work is expected to run for roughly four days or longer with meaningful recovery or handoff needs, or when the user, project, or an external coordinator explicitly requires a durable record.

Treat the requested outcome or concern as intent, not a predetermined implementation. Optimize for a plan that increases correctness, feasibility, clarity, and maintainability while reducing unnecessary complexity, risk, churn, and maintenance cost. Do not simplify one dimension by shifting material cost into another.

Ground the plan in the current source, instructions, tests, and configuration. Use your judgment to choose the design and level of detail. State genuine boundaries, acceptance conditions, likely change points, and decisive verification without adding ceremony that does not help execution.

## Reusable context

- Current project behavior is ground truth to consult before proposing; do not plan from memory of a design doc.
- Distinguish what is verified (command output, tests, source) from what is assumed in scoping and estimates.
- Choose the smallest change that satisfies the need; plan the removal of dead or duplicated paths, not new layers.
- Where a property can be enforced mechanically, name the gate (check/CI), not another instruction to follow by memory.

Request:
$ARGUMENTS
