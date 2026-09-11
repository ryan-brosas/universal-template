# Loop Variants and Phase Gates

Choose the loop from the decision at hand. Do not force an optimization experiment onto a product with no validated problem, or a broad discovery study onto a known release regression.

## Branch selection

| Situation | Start with | Evidence needed to advance | Main failure mode |
|---|---|---|---|
| Greenfield or unclear need | discovery loop | repeated task/problem evidence from relevant contexts | validating a preferred solution instead of the need |
| Known task, unproven design | concept loop | comprehension and task-path evidence across alternatives | polishing one idea too early |
| Existing flow underperforms | diagnostic loop | earliest break plus competing explanations | treating funnel location as cause |
| Release regression or incident | recovery loop | reproducible before/after behavior and bounded fix | redesigning while users remain blocked |
| High-stakes choice | safety-and-trust loop | comprehension, voluntariness, error prevention, recovery, delayed guardrails | optimizing completion while hiding harm |
| Mature flow, sufficient traffic | optimization loop | trustworthy instrumentation and controlled comparison | metric movement without user value |
| No users, analytics, or research access | low-evidence loop | deterministic checks and explicitly provisional heuristic evidence | calling inspection “validation” |

## Discovery loop: problem before interface

1. Define the behavior, context, affected people, and decision the research will inform.
2. Observe current workarounds, triggers, constraints, handoffs, failures, and consequences. Ask about concrete recent events rather than desired features.
3. Separate recurring needs from requests, stakeholder assumptions, and edge anecdotes.
4. Map the smallest end-to-end outcome and the riskiest assumption.
5. Prototype only enough to test that assumption. Advance when evidence supports a real problem, reachable audience, and plausible value; otherwise reframe or stop.

## Concept loop: structure before polish

1. Hold task and content constant while varying the uncertain information architecture, sequence, or interaction model.
2. Test comprehension, first action, expected consequence, path completion, and recovery with realistic content.
3. Compare alternatives against the same tasks. Counterbalance order when learning could favor the later variant.
4. Select by task evidence and constraints, not votes or visual preference. Then converge into the design system and run the full state matrix.

## Diagnostic loop: explain the earliest break

1. Validate events and reproduce the flow before interpreting metrics.
2. Locate the earliest consequential divergence, not merely the final abandonment point.
3. Use `diagnostic-differentials.md`: include ability, attention, comprehension, memory, effort, motivation, trust, reliability, and at least one mundane technical cause.
4. Run the cheapest disconfirming probe, then change one coherent cause.
5. Compare outcome and guardrails. Keep, revise, revert, or move the diagnosis upstream.

## Recovery loop: restore before improve

1. Write a minimal reproduction across affected device, data, permissions, network, and state.
2. Establish last-known-good behavior and severity: blocked completion, lost work, inaccessible recovery, financial/privacy harm, or cosmetic regression.
3. Restore the smallest owned contract. Preserve user state and make partial failure visible.
4. Verify the exact regression, neighboring states, and interruption/retry paths.
5. Defer broad redesign to a separate hypothesis after the baseline is restored.

## Safety-and-trust loop

Use for health, finance, privacy, children, identity, destructive actions, consent, subscriptions, and consequential AI output.

1. Define plausible harm, affected groups, reversibility, and who bears the cost of error.
2. Test whether users notice, understand, and can decline the material choice without disproportionate friction.
3. Check defaults, framing, urgency, authority, social proof, data use, pricing, renewal, cancellation, and system limitations for truthful interpretation.
4. Test prevention and recovery under stress, low literacy, interruption, assistive technology, and realistic mistakes.
5. Require stronger evidence and delayed guardrails: complaints, reversals, refunds, support burden, trust, wellbeing, and unequal outcomes. A conversion gain cannot override material harm.

## Optimization loop

1. Confirm the task already works and the event definitions, denominator, assignment, exposure, and guardrails are trustworthy.
2. Predefine the mechanism, practical effect, analysis window, segments justified in advance, and rollback threshold.
3. Change one coherent cause; avoid bundled redesigns unless the bundle is the actual treatment.
4. Inspect novelty, learning, seasonality, concurrent releases, sample-ratio mismatch, and delayed effects.
5. Ship only when the practical user outcome improves without guardrail regression. Statistical significance alone is insufficient.

## Low-evidence loop

1. Label every claim assumption, heuristic, deterministic, reported, or observed.
2. Run functional, semantic, keyboard, zoom/reflow, localization, content-extreme, loading/error/recovery, and viewport checks.
3. Compare against platform conventions and the project design system.
4. Make reversible changes and leave an instrumentation or research plan for the highest-risk unknown.
5. Report “improved against specified checks,” never “validated with users.”

## Universal phase gates

- **Frame → inspect:** task, audience/context, outcome, constraints, evidence status, and guardrails exist.
- **Inspect → hypothesize:** earliest break is evidenced and at least one competing explanation could still win.
- **Hypothesize → design:** predicted behavior, smallest coherent intervention, pass/fail, and rollback are written.
- **Design → implement:** content, states, semantics, responsive behavior, and design-system mapping are specified.
- **Implement → expose:** deterministic checks pass and no critical recovery/accessibility defect remains.
- **Expose → decide:** evidence is compared with baseline, validity limits are stated, and delayed guardrails have an owner.
- **Decide → close:** keep/revise/revert is recorded with what was learned and the next unknown—or a justified stop.
