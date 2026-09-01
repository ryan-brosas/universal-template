---
name: leverage-capture
description: "Use when meaningful work has finished and something may be worth preserving, classify it into code, references, foundations, gates, skills, or memory, and capture only that, in the cheapest appropriate form."
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
| **MEMORY** | Historical decision, failure, or context worth recall? | Session/OpenViking memory entry, not a file in the repo |
| **NOT WORTH SAVING** | Cheap to rediscover, one-off, temporary | Nothing, explicitly record the decision |

Route each candidate to the *cheapest* class that preserves it. Do not force a skill when a gate, a line of code, or a memory entry does the job. Aesthetic preferences are not gates; only demonstrated regression classes with acceptable false-positive cost become gates.

## Threshold questions (all must roughly hold for SKILL, GATE, or FOUNDATION)

1. Would this be re-derived at real cost without it?
2. Is it stable enough to document (not mid-flip)?
3. Is the representation cheaper than the re-derivation?

**FOUNDATION promotion:** create or expand a foundation only when reusable
architecture, seams, patterns, edge cases, or decisions are expensive enough
to rediscover that preserving them is cheaper than re-derivation. Record
portable upstream identity and revision so the foundation reconnects to real
source; see `../reference-driven-development/references/contract.md`.

## Workflow

1. Recall what the session/work produced (diffs, decisions, failures).
2. List candidates; classify each; drop the NOT-WORTH-SAVING ones explicitly.
3. Promote each survivor in its native form. Skill candidates follow the catalog authoring rules; gate candidates need a demonstrated regression and a low-false-positive check; foundation candidates follow `../reference-driven-development/references/contract.md` provenance rules and land in `foundation-pack/<x>-foundation/`; memory candidates go to session memory, not repo files.
4. Report: classified list, where each survivor landed, and what was deliberately not saved.

## Red Flags

- Capture ritual after every session, PR, or subagent opinion. HARD-GATE.
- Forcing everything into a skill.
- Aesthetic code-taste rules promoted to gates without demonstrated regressions.
- Saving what source/Git/manifests already say.

## Verification

Each survivor exists in its claimed form (code compiles/used; gate fails on the regression class and passes clean cases; skill passes the validator; foundation has SKILL.md with portable provenance and cited capsules on disk; memory entry retrievable). The not-saved list is explicit.

## References

- `../writing-skills/SKILL.md`, skill authoring grammar
- `../reference-driven-development/references/contract.md`, reference-checkout rules
- `../goal-setup/SKILL.md`, where multi-session decisions already live
