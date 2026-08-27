# learn - skill distillation contract

Applies to workflow-lifecycle command learn. This reference is the canonical contract (the retired global prompt file is folded into it).

## Goal
Turn a session lesson, edge case, or platform quirk into a permanent, discoverable skill in ~/.agents/skills/.

## Phase 1 - Gather
- The problem / failure / edge case.
- The exact code pattern, command, or technique that solved it.
- The friction cause.

## Phase 2 - Distill (the arbitrage)
Strip project specifics; generalize to a repeatable pattern; identify future triggers (symptoms → skill). If the lesson is a mechanical rule, prefer a gate/CI check over a prompted rule.

## Phase 3 - Position + Author
- Fits a sibling skill? Update in place (e.g. a foundation leaf). New knowledge area: new directory under ~/.agents/skills/.
- Author with the canonical template ~/.agents/templates/skill.md and the uniform grammar in writing-skills (kebab name, trigger-first description ≤1024 chars, fixed anatomy, reference capsules).
- Non-router leaves keep disable-model-invocation: true when the catalog requires it.

## Phase 4 - Make retrievable (OpenViking)
- Refresh the index when available (ov reindex / corpus) so the new skill is immediately searchable; verify with a memsearch probe. If the capability is absent, state that.

## Phase 5 - Verify
Frontmatter/description length, references listing, no duplicate names, discovery probe.

## Mutation
Skill file edits require the Schema loop / explicit approval.

## Output
1. Lesson, 2. new/updated SKILL.md path, 3. catalog registration, 4. retrievability confirmation.