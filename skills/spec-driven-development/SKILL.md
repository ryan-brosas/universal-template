---
name: spec-driven-development
description: "Use when a run is expected to last 4-10 days or span multiple sessions, requirements stay ambiguous after code inspection, or a durable cross-team contract is required; otherwise codebase-driven-development is the default."
disable-model-invocation: true
---

# Spec-Driven Development

The gated exception, not the default. The default is codebase-driven-development: code is the ground truth, the session is the artifact, and 1-2 examples one-shot the work.

## Gate: escalate here ONLY when

- The run is expected to last 4-10 days or span multiple sessions.
- Requirements remain ambiguous AFTER reading the code and its foundations.
- A durable cross-team contract must be recorded and versioned.

Otherwise use codebase-driven-development. A spec written before reading the code is a guess.

## Iron Laws

<EXTREMELY-IMPORTANT>
- **Spec after code inspection.** Read the codebase and its foundations first; then a 200-word spec prevents a 2000-line rewrite.
- **The spec is the contract.** Implementation matches the spec, not "what I imagined".
- **Spec gaps surface in the interview.** Can't write the spec = don't know what you're building.
- **Spec changes are explicit.** Change in spec = change in scope. Note it.
- **Tests derive from the spec.** Requirement without a test isn't a requirement.
</EXTREMELY-IMPORTANT>

## When to Use

4-10 day runs; multi-session work; requirements ambiguous after code inspection; a durable cross-team contract.

## When NOT to Use

One-session work; anything a 1-2 example one-shot covers; well-understood domain; bug fix with known root cause. Use codebase-driven-development.

## Spec Anatomy

```markdown
# Feature: [Name]

## Goal
[1-2 sentences. What user-visible behavior?]

## Non-goals
[What's explicitly out of scope.]

## User stories
- As a [role], I want [action], so that [outcome].

## Acceptance criteria
- [ ] [Observable behavior 1]
- [ ] [Observable behavior 2]

## Open questions
- [Question that must resolve before implementation]
```

Goal + non-goals + acceptance criteria = the minimum spec.

## Workflow

1. **Capture the request.** What's the user-observable change?
2. **Draft the spec.** Goal, non-goals, stories, criteria. May take 30-60 min — justified only for gated work.
3. **Interview the gap.** What's underspecified? Ask one question at a time.
4. **Lock the spec.** User approves.
5. **Implementation derives from the spec.** Each acceptance criterion → one or more tests.
6. **Spec changes are tracked.** A spec change is a commit message line, not a verbal "btw".

## Spec vs Plan

- **Spec** = WHAT (what we're building, what behavior)
- **Plan** = HOW (how we'll build it, in what order, with what risks)

`spec-driven-development` is for WHAT. `planning-and-task-breakdown` is for HOW. Spec first, then plan.

## Common Mistakes

Spec after code (rewrite); spec before reading the code (guess); spec too vague ("make it good"); spec too detailed (the spec IS the code, just write it); no non-goals (scope creep); no acceptance criteria (can't test); spec as a wishlist; spec never updated (drift); spec changed verbally (not in file).

## Red Flags

No goal; no non-goals; no acceptance criteria; "make it good" (not specific); spec as wishlist; no open questions; spec changed verbally; spec vs code drift; no version; "I'll know it when I see it" (not a spec).

## Anti-Patterns

**Spec after code**; **spec before code**; **vague goal**; **no non-goals**; **no criteria**; **wishlist**; **no questions**; **verbal changes**; **drift**; **"I'll know it"**; **spec = the code**.

## Pi Fabric Boundaries

**Mutation** — implementation and spec changes defer to the Schema mutation guard in AGENTS.md.
