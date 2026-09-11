# Targeted behavioral evaluation

Use pressure scenarios for a load-bearing guardrail when a known expensive
failure could recur under time pressure, ambiguous authority, or incomplete
information. For ordinary skill authoring, use `lift-evaluation.md`; behavioral
A/B testing is not required for every reference or metadata change.

## Design around the failure

Define the real outcome at risk, its evidence, and the boundary that prevents it.
Use a representative failure trace when available. Evaluate the baseline and the
smallest candidate in isolated, comparable conditions. Use fixtures or simulations
for destructive actions; never expose secrets or mutate production for a test.

Pressure should resemble the task, not force the evaluator's preferred answer.
Let the model choose any approach that satisfies the outcome and actual safety
constraints. Test a legitimate exception or adjacent out-of-scope case as well:
a guardrail that blocks valid work may cost more than it saves.

## Judge outcomes

Inspect whether the expensive failure was prevented, the task still succeeded,
and how context, calls, turns, and side effects changed. Rule citations and
obedience alone are not success criteria. A good baseline is evidence against
unnecessary instructions, not a reason to increase pressure until it fails.

When a candidate fails, distinguish missing context, tool limitations, ambiguous
ownership, and a faulty rule before adding prohibitions. Revise the smallest
relevant instruction, then repeat the affected scenario. Use more trials when
variance or consequence warrants them; no fixed score or repetition count proves
a skill is universally safe.

Record actual observations and remaining uncertainty. Do not call the skill
"bulletproof" or replace task judgment with a mandatory compliance checklist.
