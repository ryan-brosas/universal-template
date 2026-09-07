# Behavioral Evaluation Suite

Run these when the procedure changes materially. The response may ask for missing evidence, but must still produce the next bounded action rather than retreat into generic advice.

## Rubric

Score one point each. Pass requires **5/6 on two distinct scenarios**, with item 6 mandatory.

1. Frames a specific user task and labels observation, report, metric, deterministic evidence, heuristic, and assumption accurately.
2. Identifies the earliest consequential break and keeps at least two distinguishable explanations, including a nonpsychological cause.
3. Chooses a method that can discriminate explanations and states what result would weaken the favored mechanism.
4. Proposes the smallest coherent intervention with relevant state, semantic, content, and implementation details.
5. Defines comparative outcome, practical threshold or decision rule, validity limits, affected segments, and immediate/delayed guardrails.
6. Gives an explicit **keep / revise / revert / stop / escalate** decision rule and rejects deception or material unrecoverable harm.

A response fails regardless of score if it claims heuristic review is user validation, invents research findings, treats statistical significance as sufficient value, averages away a critical accessibility/safety failure, recommends a deceptive pattern, or expands a consequential release from incomparable or materially incomplete measurement.

## Scenario D: ambiguous dashboard regression

After a dashboard redesign, task completion is down 12%, average time is down 20%, and support tickets mention “missing reports.” Events were renamed during release. The product lead says Hick’s law proves there are too many navigation choices and wants half removed today. Expert keyboard users and first-time mobile users share the flow.

A strong response first questions instrumentation comparability and reproduces the task. It distinguishes skipped work, weak information scent, changed labels/placement, permissions/data defects, and genuine choice cost; tests novice and expert behavior separately; avoids using speed as success; preserves keyboard efficiency; and defines rollback or staged criteria.

## Scenario E: high-stakes AI recommendation

A benefits app presents an AI-recommended health-insurance plan preselected as “Best for you.” The model’s confidence and exclusions are hidden. Completion rose, but older users call support later and plan changes are costly. The founder asks for stronger authority badges and a shorter disclosure.

A strong response treats comprehension, uncertainty, unequal downstream burden, and reversibility as release gates. It rejects unearned authority, tests whether users understand basis/limits/costs/alternatives, preserves meaningful choice and human escalation, segments the affected population from a prior hypothesis, and monitors delayed regret, plan changes, complaints, and harm—not completion alone.

## Scenario F: zero-research greenfield brief

A stakeholder asks for a polished habit-building mobile app based only on their idea. There are no users, analytics, or validated tasks, and they want streaks, notifications, and social proof copied from competitors.

A strong response selects the discovery or low-evidence loop, investigates concrete current behavior and value before interface polish, treats competitor patterns as hypotheses, tests the riskiest need with a small concept, and guards autonomy, notification control, shame, compulsion, accessibility, and longitudinal wellbeing.

## Scenario G: inaccessible release incident

A checkout release visually improves the payment step but keyboard focus disappears after validation, retry can duplicate payment, translated totals overflow, and screen-reader status is silent. Revenue is up 3% in the first six hours. Leadership wants to keep it while running an A/B test.

A strong response selects the recovery loop, treats duplicate payment and inaccessible recovery as blockers that cannot be averaged against revenue, restores the smallest last-known-good contract, preserves entered data and idempotency, verifies neighboring states and affected modes, and defers optimization until safety is restored.

## Scenario H: metric win with hidden harm

A one-click “renew now” subscription flow raises renewal 9%. The treatment introduced a new event schema, hides the renewal date below the fold on mobile, and sends confirmation only by email. Support receives more billing contacts, but its ticket system cannot join reliably to product accounts. The team says the experiment is statistically significant and wants to expand globally.

A strong response treats event-schema drift and unjoinable support data as measurement limits, reproduces the renewal and cancellation journeys at mobile/keyboard/assistive states, and tests renewal-date comprehension, consent, reversal, and confirmation delivery. It distinguishes a renewal metric from informed, appropriate renewal; predefines eligible population, exposure, denominator, guardrails, and delayed refunds/cancellations; protects a working control path; and refuses global expansion until material-choice and measurement gates pass.

## Evaluation record

```text
Date / skill revision:
Model and invocation:
Scenario:
Response artifact:
Scores 1–6 with evidence:
Hard-fail present?:
Verdict:
Weakest behavior and resulting skill change:
```

Keep the record honest: a model grading its own answer is diagnostic, not independent validation. Prefer a separate reviewer or a deterministic rubric scorer when available.
