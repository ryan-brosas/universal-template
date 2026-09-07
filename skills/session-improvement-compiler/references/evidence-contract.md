# Evidence Contract

## Authority ladder

1. Current source, tests, runtime behavior, and explicit user requirements establish what is true now.
2. Raw current-session events, session JSONL, and supplied transcripts establish what happened.
3. Fabric recall is a locator over session evidence.
4. Hindsight recall and reflection are rebuildable projections that suggest patterns.

Never promote a projection-only claim. Follow its provenance to raw events or label it unresolved.

## Minimum evidence ledger

For each candidate record:

- lesson
- authoritative event/tool-output references
- projection references, if used
- counter-evidence and contradictions
- recurrence and affected scopes
- present-source check
- failure cost
- proposed owner and disposition
- confidence

Keep this ledger in the working response or temporary files. Do not create another permanent session summary; raw history already owns that evidence.

## Classification rules

- **CODE:** reusable implementation belongs in a source module.
- **GATE:** objective, low-false-positive regression belongs in a test, validator, lint, or CI check.
- **SKILL:** repeated procedure with meaningful judgment changes agent behavior.
- **PROJECT NOTE:** expensive rationale specific to one project.
- **FOUNDATION:** cold, revision-pinned external architecture evidence after explicit qualification.
- **NOT WORTH SAVING:** cheap to rediscover, unstable, duplicated, or one-off.

A candidate may split: procedure into a skill, objective invariant into a gate, and invocation ergonomics into a prompt.

## Existing-owner rule

Search before creating. Prefer, in order:

1. strengthen the existing deterministic gate
2. improve the existing skill capsule
3. update its reusable prompt
4. create a new narrowly triggered skill only when ownership is genuinely distinct

## Privacy and portability

Operational skills and prompts must exclude raw transcripts, secrets, credentials, client identifiers, machine-specific session IDs, current repository inventories, and temporary file paths. Evidence paths may appear in the compilation report, not in the generalized procedure.
