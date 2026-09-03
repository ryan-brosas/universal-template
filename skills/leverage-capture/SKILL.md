---
name: leverage-capture
description: "Use when work has finished and something may be worth preserving: classify it into code, references, foundations, gates, skills, project notes, or nothing, and capture only that in the cheapest form."
---

# Capture Reusable Value

## Core Principle

Preserve reusable value in its cheapest appropriate representation, not everything, and not always a skill. "Nothing worth saving" is a valid, common outcome. This replaces the old capture-after-every-session ritual.

## When to Use / NOT

- **Use when:** the same hard procedure recurred. a failure was expensive to diagnose. a non-obvious edge case will likely recur. a deterministic regression should become a gate. a reusable implementation is worth extracting. an architectural decision should be remembered. the user asks to capture the session's reusable value.
- **NOT when:** routine sessions, standard PR summaries, generic framework knowledge, anything already obvious from source, no capture ritual after every session. HARD-GATE.

## Classification (per candidate)

| Class | Test | Where it lands |
|---|---|---|
| **CODE** | Reusable implementation? | Actual code / library / project template |
| **REFERENCE** | Upstream implementation or website worth keeping? | `reference/<repo>/` checkout or `reference/web/<site>/` capture per the `reference-driven-development` contract |
| **FOUNDATION** | Reusable architecture/patterns/seams cheaper to retrieve than re-derive? | `foundation-pack/<x>-foundation/` (earned; not automatic from every repo) |
| **GATE** | Deterministic regression class with low false positives? | Test / lint / CI check / validator script |
| **SKILL** | Repeated procedure or hard-won operational method? | Skill leaf in the catalog (follows `writing-skills`) |
| **PROJECT NOTE** | Critical rationale, operational constraint, or unresolved decision: expensive to reconstruct and not obvious from source, tests, Git, configuration, or session recall? | Smallest project-appropriate tracked location |
| **NOT WORTH SAVING** | Cheap to rediscover, one-off, temporary | Nothing, explicitly record the decision |

Route each candidate to the *cheapest* class that preserves it. Do not force a skill when a gate, a line of code, or a project note does the job. Aesthetic preferences are not gates; only demonstrated regression classes with acceptable false-positive cost become gates.

## Threshold questions (all must roughly hold for SKILL, GATE, or FOUNDATION)

1. Would this be re-derived at real cost without it?
2. Is it stable enough to document (not mid-flip)?
3. Is the representation cheaper than the re-derivation?

**FOUNDATION promotion:** create or expand a foundation only when reusable
architecture, seams, patterns, edge cases, or decisions are expensive enough
to rediscover that preserving them is cheaper than re-derivation. Active owned
projects remain source, not capture candidates. Owned-project promotion
requires an explicit user request after a stable milestone; finishing a project
does not trigger promotion. External implementations remain demand-driven.
Record portable upstream identity and revision so the foundation reconnects to
real source; see `../reference-driven-development/references/contract.md`.

## Workflow

1. Recall evidence from diffs, source, tests, and selected session events. Raw session JSONL already owns history; never re-artifact it.
2. Classify possible durable promotions. A reflection may recommend a SKILL candidate, but only explicit `/compile-skill` or an equivalent direct user request may create it.
3. Explicitly drop cheap or one-off material.
4. Promote only survivors. Skill candidates follow the catalog authoring rules; gate candidates need a demonstrated regression and a low-false-positive check; foundation candidates follow `../reference-driven-development/references/contract.md` provenance rules and land in `foundation-pack/<x>-foundation/`; project notes land in the smallest project-appropriate tracked location.
5. Report what was deliberately not saved.

## Red Flags

- Capture ritual after every session, PR, or subagent opinion. HARD-GATE.
- Forcing everything into a skill.
- Aesthetic code-taste rules promoted to gates without demonstrated regressions.
- Saving what source/Git/manifests already say.
- Automatically indexing or promoting an active or newly completed owned project.
- Storing historical evidence in a new memory artifact; raw session JSONL already owns history. HARD-GATE.

## Verification

Each survivor exists in its claimed form (code compiles/used; gate fails on the regression class and passes clean cases; skill passes the validator; foundation has SKILL.md with portable provenance and cited capsules on disk; owned-project promotion records the explicit post-milestone request; project note exists in its tracked location). The not-saved list is explicit.

## References

- `../writing-skills/SKILL.md`, skill authoring grammar
- `../reference-driven-development/references/contract.md`, reference-checkout rules
- `../goal-setup/SKILL.md`, where qualified long-run post-code work state may live
