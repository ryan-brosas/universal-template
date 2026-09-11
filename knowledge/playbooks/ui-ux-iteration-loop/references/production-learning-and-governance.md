# Production Learning, Measurement Integrity, and Governance

Production data can improve a design loop only when the system can distinguish exposure, behavior, outcome, and harm. A dashboard is not evidence merely because it has a trend line.

## Measurement contract

For each decision-critical metric, define:

```text
Decision and owner:
User task and success outcome:
Eligible population and exclusions:
Exposure / assignment event and version:
Behavior, outcome, recovery, and harm events:
Denominator and time window:
Identity, deduplication, consent, privacy retention, and missingness rules; missingness rate and reason by eligibility, variant, relevant segment, and outcome:
Known instrumentation changes and reconciliation method:
Immediate and delayed guardrails:
Practical threshold, rollback threshold, and review date:
```

Events describe observable user or system actions, not inferred intent. Capture eligibility, exposure, success, failure, recovery, cancellation, and support escalation—not only impressions and conversion. Test event emission in the same state paths as the UI. A schema, identity, consent, or attribution change breaks direct historical comparison until reconciled.

## Metric integrity checks

Before acting on movement, verify:

1. The population, denominator, clock, event definitions, and version match the baseline.
2. Assignment/exposure occurred before the outcome and was not affected by the treatment’s own failure path.
3. Report missing-event rate and reason by eligibility, variant, relevant segment, and outcome. Assess whether missingness, duplicate identities, blockers, consent opt-outs, support-channel users, bots, or retries could reverse the conclusion; when material, add sensitivity bounds. Unknown material missingness fails this gate.
4. The metric represents a user outcome rather than a proxy. Pair completion with correctness, recovery, comprehension, reversals, or downstream fit.
5. The aggregate does not hide a pre-specified harmed segment, rare catastrophic failure, or shift of labor to users or support staff.
6. Concurrent releases, traffic-source changes, novelty, learning, seasonality, outages, and policy changes are recorded.

If any material check fails, classify the result as **measurement incident**, repair or triangulate it, and do not optimize from it.

## Experiment integrity

Use controlled tests only for a decision worth the cost and risk. Before exposure, specify the hypothesis, eligible population, assignment unit, treatment, primary user outcome, **estimand and analysis rule**, practical effect, minimum-detectable-effect or precision/power rationale, analysis window, multiplicity and sequential-look handling, attrition/contamination treatment, guardrails, stopping/rollback rule, and planned segments. Preserve control access to safe, working behavior.

- Randomize when feasible; verify sample-ratio and implementation parity before interpreting outcomes.
- Avoid repeated peeking and post-hoc slicing. Treat exploratory findings as new hypotheses.
- Do not ship a known accessibility, safety, privacy, or recovery defect to measure a benefit.
- Keep the experiment observable: assignment, version, exposure, errors, and rollback must be reconstructable.
- Report effect direction, uncertainty, exposure duration, limitations, and practical—not merely statistical—meaning.

When randomization is not ethical or feasible, use a staged reversible release. State that the result is operational association, not causal proof, and preserve an escalation path.

## Learning and adaptation over time

A treatment can help novices while slowing experts, or create immediate completion while degrading later trust. Track the timescale relevant to the mechanism:

| Horizon | Question | Example evidence |
|---|---|---|
| First use | Can a person discover, understand, and safely complete the task? | first action, comprehension, errors, assistive-tech success |
| Repeated use | Does learning reduce effort without hiding controls or creating brittle habits? | correction rate, shortcut use, return success, support need |
| Interrupted use | Can a person resume after delay, network loss, device change, or session expiry? | restored state, recovery completion, duplicate prevention |
| Delayed outcome | Did the choice remain appropriate and voluntary? | reversal, cancellation, refund, appeal, regret, complaints |
| System impact | Did the intervention displace risk or labor? | operator workload, support burden, unequal outcomes, accessibility debt |

Segment from a mechanism declared before analysis: for example novice versus expert, keyboard versus pointer, localized versus source language, or low-bandwidth versus typical network. Never infer capability or collect sensitive attributes beyond what is necessary, lawful, and privacy-preserving.

## Governance and release record

The governance record is canonical. Assign one **iteration/treatment ID** before implementation; the handoff, code/config version, instrumentation schema, acceptance artifacts, and decision ledger must reference it. Any treatment, threshold, schema, or release change updates this record before evaluation resumes.

Every consequential iteration has an accountable decision record:

```text
Iteration/treatment ID:
Decision / accountable owner / date:
Evidence and source limits:
Eligible population and excluded or affected groups:
Claim type: normative | descriptive | predictive | causal:
Treatment, versions, and variables held constant:
Expected benefit, plausible harms, severity, detectability, reversibility:
Accessibility, privacy, security, and policy constraints:
Primary outcome / guardrails / metric integrity status:
Release scope / monitoring owner / rollback or escalation path:
Review dates for delayed outcomes:
Decision: keep | revise | revert | stop | escalate:
```

Escalate rather than optimize when the intervention could create material, hard-to-detect, or irreversible harm; affects a protected or underrepresented group without adequate evidence; makes a consequential automated recommendation; conflicts with law, policy, WCAG target, privacy/security requirements, or a user’s informed choice. Publish only claims the evidence supports.
