---
title: ui-ux-iteration-loop
summary: Use when improving or designing an interface through repeated UI/UX iterations, especially when feedback is vague, a screen looks usable but a task underperforms, or psychology and UI heuristics must become testable design changes rather than decoration.
kind: playbook
---

# UI/UX Iteration Loop

## Core Principle

Optimize a user task, not a screen. Treat every heuristic and psychology principle as a causal hypothesis until observed behavior supports it; change the smallest coherent variable, test it, and retain only demonstrated improvements.

## When to Use / NOT

- **Use when:** creating or improving a flow, diagnosing friction, turning “make it better” into evidence, or iterating from prototype through validated UI.
- **NOT when:** exact source fidelity is the goal (`pixel-perfect`); the question only needs a throwaway mockup (`prototype`); mapping cross-channel journeys precedes design (`app-experience-mapping`); or a finished app needs a broad black-box release audit (`black-box-experience-review`).

## Workflow

1. **Choose the loop and frame one task.** Use `references/loop-variants-and-gates.md`; record user/context, entry, outcome, constraints, guardrails, one behavioral measure, and conditional service/channel seams with their recovery owner. Tag claims observed, reported, deterministic, heuristic, or assumed.
2. **Capture the baseline.** Walk representative viewports, content, states, and input modes. Record success, errors, recovery, effort, and accessibility barriers. No users or analytics means provisional evidence, not validation.
3. **Find the earliest break.** Describe behavior before theory. Use `references/diagnostic-differentials.md`; keep competing psychological and technical causes alive.
4. **Commit to a mechanism and prediction.** Use `references/mechanism-cards.md` and `references/evidence-foundations-and-limits.md`. State claim type, higher-authority constraints, what supports or weakens it, then define treatment, pass/fail, guardrails, and rollback before editing. Retrieve only enough external evidence to resolve a decision-changing unknown: name source class, freshness need, budget, and stop condition.
5. **Design the smallest coherent intervention.** Use `references/interface-heuristics.md` and record apply/adapt/reject for relevant `references/pdf-tip-crosswalk.md` rows. Preserve conventions, control, state, and design-system consistency; variants must test named uncertainty.
6. **Specify and implement the behavior.** Use `references/implementation-handoff.md`, then `frontend-ui-implementation` for concrete typography, forms, layout, navigation, visual/data, and async-state frontend work. Assign the canonical iteration/treatment ID and cover relevant transitions, recovery, semantics, content extremes, responsiveness, instrumentation, seams, and ownership—not only the ideal screenshot.
7. **Evaluate in layers.** Run deterministic functional/accessibility checks, rendered inspection, task evidence, then controlled metrics when justified. Apply `references/inclusive-safety-and-welfare.md` and `references/production-learning-and-governance.md`; compare baseline, affected segments, measurement integrity, immediate outcomes, and delayed guardrails.
8. **Decide and loop.** Record keep/revise/revert, confidence, side effects, what was ruled out, and the next unknown. Stop at the phase gate—not when the screen merely looks polished.

## Priority

Triage by harm severity and reversibility first, then task criticality and reach. Low confidence raises research priority; it never excuses plausible material harm. Accessibility, lost work, blocked completion, deception, and unrecoverable errors outrank novelty.

## Red Flags

- Applying a checklist wholesale or naming a law as proof.
- Inferring user intent from aesthetics, stakeholder preference, or the designer’s own behavior.
- Changing navigation, copy, hierarchy, and interaction together so causality disappears.
- Optimizing clicks or conversion by hiding costs, defaults, cancellation, or alternatives.
- Calling a screenshot review “user validation.”

## Verification

Deliver a baseline, evidence-tagged break point, hypothesis, before/after renders, state matrix, checks performed, result against threshold and guardrails, and keep/revise/revert decision. A loop without comparative evidence remains an experiment, not an improvement.

## References

- `references/loop-variants-and-gates.md`, branch selection and phase gates.
- `references/psychology-lenses.md` and `references/mechanism-cards.md`, diagnosis, predictions, and disconfirmation.
- `references/diagnostic-differentials.md`, competing explanations for ambiguous symptoms.
- `references/interface-heuristics.md` and `references/pdf-tip-crosswalk.md`, contextual source-PDF checks.
- `references/experiment-and-evidence.md` and `references/evidence-foundations-and-limits.md`, method selection, inference limits, standards, and claim boundaries.
- `references/inclusive-safety-and-welfare.md`, exclusion, harm, comprehension, and delayed guardrails.
- `references/production-learning-and-governance.md`, measurement integrity, experiment governance, longitudinal learning, and release accountability.
- `references/implementation-handoff.md`, state, semantic, content, instrumentation, and acceptance contracts.
- `references/behavior-evaluations.md` and `references/behavior-evaluation-results.md`, adversarial rubric and results.
- `references/sources-and-validation.md`, source boundaries and critical synthesis.
