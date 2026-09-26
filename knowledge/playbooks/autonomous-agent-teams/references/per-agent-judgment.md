# Verify judgment inside ordinary agent runs

A coordinator consulting Jev does not establish that specialists can consult it.
Use this when enabling per-agent judgment or assessing claims that a team is now
autonomous or efficient. For question design and backend contracts, use
[typed judgment workflows](../../typed-judgment-workflows/README.md).

## Separate the claims

| Claim | Evidence needed |
| --- | --- |
| Configured | Policy and intended capability exist. |
| Integrated and tested | Registration, exposure, dispatch, dependencies, and failure paths are exercised. |
| Deployed | The running process uses the tested implementation and configuration. |
| Observed use | A receipt belongs to a specific recipient run; distinguish prompted from unprompted use. |
| Useful or efficient | Comparable tasks improve against the direct workflow, accounting for failures, time, cost, and human intervention. |

Do not collapse these into "all agents use Jev." State eligible run types,
exclusions, and the sample actually observed. A healthy service proves neither
tool exposure nor successful judgment. One receipt proves neither widespread
uptake nor continuously running autonomy.

## Trace the recipient's path

Follow capability construction through every execution process, tool registration,
per-run selection, matching instruction injection, guarded dispatch, backend
response, and durable receipt. Check the actual recipient, not just its parent.
Use one shared adapter for team-level and per-agent judging rather than divergent
protocol implementations.

Exercise the claimed contexts: direct chat, rooms, routines, and delegated runs
can have different gates. Record intentional exclusions, including untrusted
channel input or constrained workers; do not widen their authority to make an
"all bots" claim true. Advertise guidance only where the capability is exposed.
Credential configuration is not proof that the backend can answer.

## Probe behavior, not presentation

Use authorized synthetic tasks with bounded cost and external effects disabled
at the execution boundary. First ask a normal decision task without naming the
judge; use a separate, unprimed context for an explicit capability probe if needed.
The explicit probe proves reachability, not spontaneous adoption.

Capture the returned run identity. Wait boundedly for that exact run's terminal
state; a task title, progress block, old assistant message, or fixed sleep is not
completion. Report timeout or failure rather than silently treating it as success.
Use the current contract and storage mapping instead of guessing API or table names.

Join receipts to the run and inspect status, typed questions and answers, answering
backend, usage, and budget accounting. A bot saying "I used Jev" is not a receipt.
Read answers against their rubrics before comparing them with the final response:
different choices for first and last priority do not demonstrate disagreement.

## Bound use and assess benefit

Keep credentials, limits, data-sharing policy, and execution authority host-owned.
Batch independent questions; skip exact checks and repeated judgments over
unchanged evidence. Unavailable, disabled, malformed, and exhausted outcomes need
explicit fallbacks, not fabricated verdicts.

Completed-receipt replay depends on execution identity. Repeating the same text
with a new identity is not necessarily cached; receipt persistence does not make
inference billing exactly once. A per-run call limit is neither a spend cap nor a
fleet-wide limit across scheduled runs.

Compare representative tasks with and without judgment, including failure cases.
Measure outcome quality, elapsed time, total calls/cost, and human intervention;
call frequency alone is not success. Verify scheduling, delegation, recovery,
model switching, and retained learning separately. A judgment tool implements
none of those by itself.
