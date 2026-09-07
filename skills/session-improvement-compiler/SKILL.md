---
name: session-improvement-compiler
description: "Use when the user explicitly asks to turn current or historical session lessons, Fabric history, Hindsight memory, or a retrospective into durable improvements; triangulates evidence, improves the existing owner first, and routes outcomes to skills, gates, code, notes, or nothing."
invocation: manual
disable-model-invocation: true
---

# Session Improvement Compiler

## Core Principle

Compile evidence, not anecdotes. Raw session events and current source establish truth; Fabric recall locates evidence, while Hindsight recall/reflect proposes patterns. Every durable promotion must remain traceable to authoritative evidence.

## When to Use / NOT

- **Use when:** the user explicitly requests continual improvement, session-to-skill compilation, or improvement from Fabric/Hindsight memory.
- **NOT when:** merely recalling or reflecting, at every session end, or when no promotion was requested.

## Workflow

1. **Bound the evidence.** Default to the current project and current session. Record named sessions, user-provided transcripts, and exact questions. Cross-project/global evidence requires explicit scope.
2. **Triangulate cheaply.** Read the smallest sufficient raw event ranges. Use Fabric recall to locate ranges and Hindsight recall/reflect to surface candidate patterns. Projection output is a lead, never independent proof. If a projection provider fails, continue from accessible raw evidence rather than inventing its conclusion.
3. **Build an evidence ledger.** For each candidate, record supporting events/tool outputs, counter-evidence, recurrence, current-source status, confidence, and scope. Preserve user corrections and failed rationalizations verbatim where useful (`references/evidence-contract.md`).
4. **Classify before writing.** Apply `leverage-capture`: CODE, GATE, SKILL, PROJECT NOTE, FOUNDATION, or NOT WORTH SAVING. Objective regression classes prefer deterministic gates. Repeated operational judgment may earn a skill. Project facts do not become global skills.
5. **Find the owner.** Search existing skills, prompts, tests, validators, and docs. Improve the narrowest existing owner before creating another skill. Reject additions that create trigger collisions or duplicate truth.
6. **Promote deliberately.** This invocation is an explicit promotion request. Carry forward confirmed, in-scope defects from earlier passes: fixing an easier neighbor or documenting the gap does not dispose of them. Implement each qualified repair or name a concrete blocker (missing authority, dependency, evidence, or unsafe scope); do not silently reclassify unfinished work as nothing worth saving. Follow `writing-skills` for skill changes; preserve canonical prompt/skill separation; keep raw transcripts and private identifiers out of operational instructions.
7. **Verify end to end.** Run affected validators, catalog/collision checks, deterministic gates, prompt installation checks, and behavior pressure tests. RED may come from the selected real session; GREEN must demonstrate that the revised workflow rejects the same rationalization twice.
8. **Report disposition.** Reconcile the report against every ledger candidate, including prior deferrals; a previous completion report is not closure evidence. List evidence used, files changed, checks, unresolved uncertainty, and material deliberately not saved. Stop when promotions are verified or no candidate qualifies.

## Red Flags

- Treating Hindsight or a summary as primary evidence.
- Dumping entire session logs into model context or skill files.
- Creating a new skill before searching for an existing owner.
- Encoding deterministic requirements only as prose.
- Promoting a one-off preference, stale fact, or project inventory.
- Saying “learned” without a verified behavioral or mechanical change.

## Verification

The skill validator and catalog pass; prompt references resolve; objective gates catch the observed regression; behavior tests pass twice; every promotion cites authoritative evidence; the not-saved list is explicit.

## References

- `references/evidence-contract.md`, source authority, ledger, classification, and privacy rules.
- `references/behavior-tests.md`, real RED cases and GREEN acceptance.
- `../leverage-capture/SKILL.md`, cheapest durable representation.
- `../writing-skills/SKILL.md`, skill authoring and validation.
