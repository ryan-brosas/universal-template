---
title: leverage-capture
summary: Use when capture is explicitly requested, a hard procedure recurs, or an expensive failure or milestone yields a concrete reusable candidate; classify it into code, references, gates, skills, project notes, or nothing.
kind: playbook
---

# Capture Reusable Value

## Core Principle

Preserve reusable value in its cheapest appropriate representation, not everything,
and not always a skill. "Nothing worth saving" is a valid, common outcome. This
replaces the old capture-after-every-session ritual.

Knowledge about how we work may deserve to persist. Precomputed descriptions of
code an agent can cheaply retrieve again do not: source, tests, and Git already
hold that truth, so do not duplicate it.

## When to Use / NOT

- **Use when:** the same hard procedure recurred; a failure was expensive to
  diagnose; a non-obvious edge case will likely recur; a deterministic regression
  should become a gate; a reusable implementation is worth extracting; an
  architectural decision should be remembered; the user asks to capture the
  session's reusable value.
- **NOT when:** routine sessions, standard PR summaries, generic framework
  knowledge, anything already obvious from source, or a capture ritual after every
  session. HARD-GATE.

## Classification (per candidate)

| Class | Test | Where it lands |
|---|---|---|
| **CODE** | Reusable implementation? | Actual code / library / project template |
| **REFERENCE** | Upstream implementation or website worth keeping? | `reference/<repo>/` checkout or `reference/web/<site>/` capture per the `reference-driven-development` contract |
| **GATE** | Deterministic regression class with low false positives? | Test / lint / CI check / validator script |
| **SKILL** | Repeated procedure or hard-won operational method? | Skill leaf in the catalog (follows `writing-skills`) |
| **PROJECT NOTE** | Critical rationale, operational constraint, or unresolved decision, expensive to reconstruct and not obvious from source, tests, Git, configuration, or session recall? | Smallest project-appropriate tracked location |
| **NOT WORTH SAVING** | Cheap to rediscover, one-off, temporary | Nothing, explicitly record the decision |

Route each candidate to the *cheapest* class that preserves it. Do not force a
skill when a gate, a line of code, or a project note does the job. Aesthetic
preferences are not gates; only demonstrated regression classes with acceptable
false-positive cost become gates.

## Threshold questions (all must roughly hold for SKILL or GATE)

1. Would this be re-derived at real cost without it?
2. Is it stable enough to document (not mid-flip)?
3. Is the representation cheaper than the re-derivation?

A repository summary fails these tests: source is retrievable on demand and a
summary only drifts from it. Do not add one because a repository was studied.

## Workflow

1. Recall evidence from diffs, source, tests, and selected session events. Raw
   session JSONL already owns history; never re-artifact it.
2. Classify possible durable promotions. A reflection may recommend a SKILL
   candidate, but only explicit `/compile-skill`, `/compile-session-improvements`,
   or an equivalent direct user request may create it.
3. Explicitly drop cheap or one-off material.
4. Promote only survivors. Skill candidates follow the catalog authoring rules;
   gate candidates need a demonstrated regression and a low-false-positive check;
   references follow `../reference-driven-development/references/contract.md`;
   project notes land in the smallest project-appropriate tracked location.
5. Report what was deliberately not saved.

## Red Flags

- Capture ritual after every session, PR, or subagent opinion. HARD-GATE.
- Forcing everything into a skill.
- Adding a repository summary, architecture digest, or source index to the template
  because a repository was studied.
- Aesthetic code-taste rules promoted to gates without demonstrated regressions.
- Saving what source/Git/manifests already say.
- Storing historical evidence in a new memory artifact; raw session JSONL already owns history. HARD-GATE.

## Verification

Each survivor exists in its claimed form (code compiles/used; gate fails on the
regression class and passes clean cases; skill passes the validator; reference
follows the contract; project note exists in its tracked location). The not-saved
list is explicit.

## References

- `../writing-skills/README.md`, skill authoring grammar
- `../reference-driven-development/references/contract.md`, reference rules
- `../goal-setup/README.md`, where earned recovery or handoff state may live
