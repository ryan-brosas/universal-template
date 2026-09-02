# Implement the requested work

Implement the request below end to end.

Treat the user's concern and any suggested approach as signals, not a predetermined solution, unless the user explicitly makes the approach a requirement. Optimize toward the Pareto frontier: increase capability, correctness, usability, and maintainability while reducing unnecessary complexity, duplication, host-specific glue, and maintenance burden. Do not gain in one dimension by materially degrading another unless the tradeoff is justified.

Preserve unrelated changes and existing public contracts unless the request requires otherwise. Inspect enough of the current behavior, callers, tests, and validators to make a sound change. Use your judgment to choose the implementation rather than adding machinery without a demonstrated need.

Verify the result with targeted tests and direct behavioral probes. Inspect failures, iterate when needed, and finish with the changed paths, evidence, and known limitations.

## Reusable context

- Source, tests, and runtime behavior are primary authority; summaries, skills, and model opinion do not override them for the change you own.
- Keep the diff at one coherent scope; no unrelated churn, no hidden rewrites; preserve existing public contracts and unrelated user changes.
- Evidence beats claims: run the strongest checks that exist, show real output, never claim a check you did not run.
- Add machinery only when the code demonstrates the need; anything mechanically enforceable is a gate, not a prompt.
- DRY is earned at the second real copy; YAGNI blocks nothing that is already required.

Request:
$ARGUMENTS
