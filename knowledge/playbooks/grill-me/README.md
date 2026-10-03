---
title: grill-me
summary: Use when a proposal, ADR, PRD or spec needs its assumptions and failure cases challenged before implementation.
kind: playbook
---

# Stress-test a proposal

Investigate whether the plan meets its goal and where it could fail. This is
scrutiny of an existing direction, not a prerequisite for every coding task.
Use [brainstorming](../brainstorming/README.md) when the direction itself is still
being formed. For scrutiny centered on project terminology and documented
choices, use research's [grill-with-docs](../grill-with-docs/README.md) extension.

## Workflow

1. Read the proposal, requirements and relevant project evidence. Answer what
   source can establish rather than asking the user to repeat it.
2. Identify consequential assumptions, alternatives and failure cases. Choose
   the question whose answer most affects the decision; do not walk a checklist
   of every imaginable risk.
3. Ask one question at a time when user judgment is needed, explaining the
   trade-off and a recommendation where evidence supports one. Wait for the
   answer before pursuing a dependent question. Do not force the user to express
   uncertainty about facts already established.
4. Reassess the direction as evidence arrives. Stop when consequential uncertainty
   is resolved, the plan needs reconsidering, or further questions add no value.

Useful questions concern the cost of a mistaken assumption, meaningful scale
changes, an external dependency's limits, the smallest informative experiment,
recovery or rollback, and explicit non-goals. Select what applies; neither a
question count nor finding a flaw proves the review was useful.

## Outcome

Summarize the strengthened or rejected direction, resolved assumptions and
remaining blocked decisions in the conversation. Preserve agreed rationale in
existing project documentation when that is part of the task. Do not create a
separate grilling document or start implementation without authorization.
