# Experiment and Evidence Protocol

## Frame

```text
Task:
User and context:
Entry → intended outcome:
Observed / reported / assumed:
Primary behavioral measure:
Guardrails (accessibility, errors, trust, retention, support, revenue):
Constraint:
```

Choose a task measure that represents user success. Clicks and time are ambiguous: fewer can mean efficiency or abandonment; more can mean engagement or confusion. Pair them with completion, correctness, recovery, comprehension, or satisfaction.

## Baseline evidence by question

Evidence is not one ladder. Name the limit and use the source suited to the decision:

- **Assumption:** stakeholder/design belief; useful only to choose what to inspect.
- **Heuristic inspection:** predicts likely friction; does not show that users experience it.
- **Deterministic check:** semantics, contrast, focus order, layout, state, and functional tests establish objective behavior under specified conditions.
- **Observed task:** representative participants attempt a realistic task; exposes behavior and plausible mechanisms, but does not estimate population prevalence.
- **Product behavior:** funnels, errors, abandonment, search, support, and recovery data show product-context sequence and scale when measurement is sound, but may not explain cause.
- **Controlled comparison:** provides the strongest causal estimate when assignment, sample, duration, analysis plan, and guardrails are credible.

Normative constraints remain binding regardless of measurement movement. Triangulate when stakes are high: analytics says **where**, task observation often says **how**, interviews can suggest **why**, and a controlled comparison estimates **whether this change caused movement**.

## Match the method to the uncertainty

| Unknown | Cheapest useful method | What it establishes | Common failure |
|---|---|---|---|
| Can the interface technically work? | state/functional test | objective behavior under specified conditions | testing only the happy path |
| Can people perceive or operate it? | accessibility inspection plus keyboard/assistive-tech task | barriers in the tested modes | treating an automated scan as conformance |
| Where does a journey break at scale? | validated analytics, search, errors, support data | prevalence and sequence, not cause | bad event definitions or survivorship bias |
| What do people understand or expect? | moderated task, first-click, tree test, teach-back | behavior and mental-model evidence | leading, teaching, or asking preference only |
| What needs exist before a solution? | contextual inquiry, interview, diary, ticket synthesis | generative themes and contexts | treating stated intent as observed behavior |
| Which design performs better? | counterbalanced comparative usability test | relative behavior in the tested sample | changing many causes without knowing why |
| Did one change cause product movement? | randomized controlled experiment when feasible | causal estimate within assignment and measurement limits | peeking, underpowered slices, novelty effects |
| Is a risky release safe? | reversible staged rollout with guardrails | operational evidence and bounded exposure | calling before/after correlation causal |

### Lightweight study protocol

1. Define the decision the study will change and what result would reverse the current preference.
2. Recruit participants who match the relevant behavior, knowledge, constraints, and assistive modes—not merely convenient demographics.
3. Use realistic goals and data. Give the outcome, not instructions that reveal the path.
4. Pilot once for broken tasks or instrumentation. During sessions, avoid praise, defense, explanation, and leading follow-ups.
5. Capture behavior before interpretation: first action, sequence, hesitation, error, recovery, outcome, and exact spontaneous language.
6. Analyze by task and mechanism. Preserve contradictory cases; frequency in a small qualitative sample is not population prevalence.
7. Report participant/context limits, missing segments, moderator or observer effects, and confidence. Do not manufacture statistical certainty.

### Validity threats

Check instrumentation drift, sample mismatch, learning/order effects, novelty, seasonality, concurrent releases, network/device differences, missing denominators, selective reporting, and guardrail lag. Predefine the practical threshold and analysis window when causal claims matter. If the method cannot support causality, say “associated with” or “observed after,” not “caused.”

## Diagnose and hypothesize

Write observations without theory first:

```text
Observation: 4/6 participants opened Billing before Plans and returned.
Impact: delayed plan comparison; 2 abandoned.
Possible mechanisms: weak information scent; mental-model mismatch.
Alternatives: unfamiliar label; navigation position; missing overview.
```

Then commit to one test:

```text
For [user/context], changing [coherent cause] from [baseline] to [treatment]
will improve [behavior/threshold] because [mechanism],
without worsening [guardrails].
Pass: ...  Fail: ...  Roll back if: ...
```

“One coherent cause” may require coordinated UI details—for example, an actionable inline error needs copy, placement, focus, announcement, and preserved input. Do not split a usable intervention merely to pursue artificial purity.

## Evaluation sequence

1. **Functional/state:** complete the task and force every relevant state and recovery path.
2. **Accessibility:** automated checks plus keyboard and assistive-technology inspection; automation is not complete conformance.
3. **Visual:** compare before/after at representative viewports, zoom, themes, long content, and localization.
4. **Usability:** give the goal, not step-by-step instructions. Record first action, success, errors, hesitation, recovery, and spontaneous comments. Avoid teaching the design.
5. **Product:** validate event definitions and denominator; segment only where a plausible mechanism predicts differences. Predefine practical effect and guardrails; statistical significance alone is not product value.

If controlled testing is impossible, use a reversible staged release and label causal confidence accordingly. Do not invent sample sizes or significance thresholds without expected effect, baseline rate, variance, and risk.

## Decision ledger

```text
Iteration/treatment ID (links to canonical governance record):
Iteration / date:
Evidence and confidence:
Earliest break:
Hypothesis and intervention:
Baseline → result:
Guardrails / side effects:
Decision: keep | revise | revert
What this rules out:
Next highest-risk unknown:
Artifacts: renders, recordings, queries, tests
```

## Stop conditions

Stop the current loop when one condition is true:

- success reaches the predefined practical threshold and guardrails hold;
- repeated credible tests show no meaningful gain, so the diagnosis changes;
- a higher-severity problem supersedes it;
- evidence shows the failure belongs to another journey, service seam, audience, or product proposition;
- further certainty costs more than the reversible decision warrants.

Do not stop because the screen looks polished, stakeholders prefer it, all checklist items were applied, or one metric moved while trust/accessibility regressed.
