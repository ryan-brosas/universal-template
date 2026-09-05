# Evaluate task lift

Use this when proposing a hot skill, changing a load-bearing skill materially,
resolving overlapping owners, reviewing a large loader, or investigating a skill
that appears to slow real work. This is an evaluation lens, not required CI, a
universal benchmark suite, or a runtime scoring engine.

## Hypothesis before instructions

Describe the task and the missing capability in a few sentences:

- What does the model repeatedly get wrong or rediscover without this skill?
- What unique context or shortcut does it supply? What work should disappear?
- Which choices remain with the model and the project?
- Which constraints address demonstrated expensive failures rather than taste?

A real task, failure trace, or repeated session pattern is stronger evidence than
an invented need. Do not manufacture failure to justify a candidate. If the
baseline already succeeds efficiently, compression, a reference, or no skill may
be the right result.

## A bounded comparison

Choose a representative task with outcome criteria independent of the candidate's
wording. Include a boundary case when misuse has meaningful cost. Capture the
starting source/tree, task input, model and host, tool availability, and relevant
project context. Use isolated runs or restored fixtures so the candidate run does
not inherit the baseline's answers, edits, or failures. Never replay destructive
or external effects against real user data just to establish a baseline.

Run without the candidate, then with its smallest useful version. Keep conditions
comparable. Existing traces can substitute when replay is unsafe or costly, but
record the differences and weaker confidence. Repeat or counterbalance runs only
when variance or decision impact warrants it; no fixed pass count is required.

Compare observed evidence:

| Dimension | Evidence |
|---|---|
| Outcome | Acceptance checks, usable result, source-grounded accuracy |
| Errors | Failed calls, missed consumers, regressions, recovery success |
| Effort | Model turns, tool calls, repeated reads, source exploration |
| Context | Loader and references actually opened, activated schemas, output bytes |
| Side effects | Unrelated edits, persistent documents, unnecessary setup |
| Freedom | Valid approaches blocked, new architecture imposed without need |

Count what was actually observed. Bytes and token estimates are different units;
static loader size is not measured request growth. Mark unavailable telemetry as
unknown rather than zero. A correct rule citation or completed checklist is not
an outcome metric. More effort can be worthwhile when it prevents a demonstrated
high-cost failure; fewer calls do not excuse lower quality.

## Match proof to the capability

| Skill type | Useful proof |
|---|---|
| Tool/integration | Fewer failed calls, necessary ordering, recovery from real errors |
| Context | Correct answer with less source exploration |
| Procedure | Equal or better work with fewer turns or errors |
| Guardrail | Expensive failure prevented without blocking legitimate work |
| Router | Correct destination with less context and no harmful collisions |
| Foundation | Faster source-grounded answer without unsupported claims |
| Simple reference | Relevant information found and used; current links and facts |
| Deterministic helper | Fixture/unit/integration execution, including its caller |

Simple references and metadata edits need no behavioral A/B ritual. For a
load-bearing guardrail, `testing-methodology.md` covers targeted pressure tests.

## Decide, do not accumulate rules

Keep a candidate when its benefit justifies its loaded context and maintenance.
Compress when useful mechanics are buried; demote when useful but specialized;
merge when owners duplicate decisions; retire when it adds generic advice or no
useful capability. Routing overlap can be legitimate: establish precedence rather
than demanding artificial exclusivity.

Preserve a compact comparison only if it aids future decisions: task/fixture,
conditions, candidate revision, observations, unknowns, and disposition. Use the
existing PR or task record when sufficient; no mandatory registry or report file.
If no comparison ran, say so. Exact validation can establish a valid unpublished
candidate, not demonstrated lift or grounds for automatic hot promotion.
