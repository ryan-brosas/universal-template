---
name: brainstorming
description: "Use when a rough idea needs clarification before implementation, resolve ambiguous direction by grounding in what exists, framing the problem, exploring real alternatives, and deciding."
---

# Brainstorming

## Core Principle

Brainstorming produces **decision quality**, not document volume. It grounds in what already exists before asking the user anything, explores only genuine alternatives, and ends in a decision with a routed next step. Skip it whenever the request is clear and routine.

## When to Use / NOT

- **Use when:** vague product/feature direction, multiple plausible approaches where the choice is load-bearing, "what if we…" with real ambiguity, a new project whose purpose is not yet clear.
- **NOT when:** clear concrete requests (implement directly), bug fixes with a known root cause, mechanical refactors, one-liners. Adding a retry to an API call is not a brainstorm. "Prototype this" → `prototype`, not a design conversation.

## Workflow

### 1. GROUND, inspect the available truth first

- **Existing repository:** read local instructions, the relevant implementation, nearest patterns, existing tests, the architecture seam involved. Ask the repository before asking the user, never ask a question the code can already answer.
- **Greenfield:** ground in the user's problem, audience, constraints, and existing external requirements. Do not fabricate existing architecture.

### 2. FRAME, capture only the load-bearing frame

```
Outcome / User / Problem / Success / Constraints / Unknowns
```

This is a thinking frame, not a PRD, do not write it to disk by default. If it never becomes load-bearing, the conversation is the artifact.

### 3. EXPLORE, only real alternatives

Present multiple variants (A/B/C) only when they materially differ in architecture, UX, scope, tradeoff, or implementation strategy. Three cosmetic rewrites of one solution is ceremony. If the repository already has an obvious consistent pattern, recommend it directly and say why.

### 4. DECIDE, end in a decision

```
Chosen direction · Why · Rejected alternatives worth remembering · Open decision(s) · Recommended next step
```

Then route:

- **clear + normal** → implement directly
- **needs runnable learning** → `prototype`
- **durable / high-risk / multi-session** → `goal-setup`

## Question policy

Ask the **fewest high-value questions** required to close load-bearing uncertainty, questions that can materially change scope, user-visible behavior, architecture, data, permissions, rollout, success criteria, or irreversible constraints. Bundle tightly related questions. Never interrogate the user about facts the repository, manifests, or docs can answer.

## Artifact policy

Normal brainstorming: the conversation is the artifact, no `design.md`, `brainstorm.md`, or `plan.md` by default. When the work turns out durable/high-risk/multi-session, promote the decided frame into `goal-setup` (one artifact, there).

## Red Flags

- Asking questions the repository already answers. HARD-GATE.
- Manufacturing variant ceremony when one consistent option exists.
- Writing planning files for normal brainstorming.
- Blocking clear work behind a design ritual the user did not ask for.
- Silent assumptions, pick and name the stack/approach explicitly.

## Verification

The exchange ends with a stated decision (or an explicit blocked-on-user note listing the exact missing decisions), grounded in inspected repository truth, with the next step routed. No planning files exist unless promotion to `goal-setup` happened.

## References

- `../prototype/SKILL.md`, cheap runnable learning
- `../goal-setup/SKILL.md`, durable execution contract
