---
name: leverage-capture
description: "Use after meaningful work to classify what is worth preserving — into code, references, gates, skills, or memory — and capture only that, in the cheapest appropriate form."
---

# Leverage Capture

## Core Principle

Preserve reusable leverage in its cheapest appropriate representation — not everything, and not always a skill. "Nothing worth saving" is a valid, common outcome. This replaces the old capture-after-every-session ritual.

## When to Use / NOT

- **Use when:** the same hard procedure recurred; a failure was expensive to diagnose; a non-obvious edge case will likely recur; a deterministic regression should become a gate; a reusable implementation is worth extracting; an architectural decision should be remembered; the user asks to capture the session's leverage.
- **NOT when:** routine sessions, standard PR summaries, generic framework knowledge, anything already obvious from source — no capture ritual after every session. HARD-GATE.

## Classification (per candidate)

| Class | Test | Where it lands |
|---|---|---|
| **CODE** | Reusable implementation? | Actual code / library / project template |
| **REFERENCE** | Upstream implementation worth keeping? | `reference/<repo>/` checkout per `reference-contract` |
| **GATE** | Deterministic regression class with low false positives? | Test / lint / CI check / validator script |
| **SKILL** | Repeated procedure or hard-won operational method? | Skill leaf in the catalog (follows `writing-skills`) |
| **MEMORY** | Historical decision, failure, or context worth recall? | Session/OpenViking memory entry — not a file in the repo |
| **NOT WORTH SAVING** | Cheap to rediscover, one-off, temporary | Nothing — explicitly record the decision |

Route each candidate to the *cheapest* class that preserves it. Do not force a skill when a gate, a line of code, or a memory entry does the job. Aesthetic preferences are not gates; only demonstrated regression classes with acceptable false-positive cost become gates.

## Threshold questions (all must roughly hold for SKILL/GATE)

1. Would this be re-derived at real cost without it?
2. Is it stable enough to document (not mid-flip)?
3. Is the representation cheaper than the re-derivation?

## Workflow

1. Recall what the session/work actually produced (diffs, decisions, failures).
2. List candidates; classify each; drop the NOT-WORTH-SAVING ones explicitly.
3. Promote each survivor in its native form. Skill candidates follow the catalog authoring rules; gate candidates need a demonstrated regression and a low-false-positive check; memory candidates go to session memory, not repo files.
4. Report: classified list, where each survivor landed, and what was deliberately not saved.

## Red Flags

- Capture ritual after every session, PR, or subagent opinion. HARD-GATE.
- Forcing everything into a skill.
- Aesthetic code-taste rules promoted to gates without demonstrated regressions.
- Saving what source/Git/manifests already say.

## Verification

Each survivor exists in its claimed form (code compiles/used; gate fails on the regression class and passes clean cases; skill passes the validator; memory entry retrievable). The not-saved list is explicit.

## References

- `../writing-skills/SKILL.md` — skill authoring grammar
- `../references/reference-contract.md` — reference-checkout rules (via catalog `references/`)
- `../goal-setup/SKILL.md` — where multi-session decisions already live
