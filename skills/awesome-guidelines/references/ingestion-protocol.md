# Ingestion protocol — learn deep, note it, then skill it

Applies to every row in `ingestion-index.md`. **Shallow bullet summaries are not done.**

## Phase 1 — Learn deep

1. **Collect sources** — every URL listed on the awesome-guidelines row + one authoritative secondary (e.g. Git `SubmittingPatches`, tbaggery on commit messages).
2. **Read for behavior** — not headings. Extract:
   - invariants (must never break)
   - flows (ordered transitions)
   - precedence / conflict rules
   - FAQ edge cases the source explicitly answers
   - anti-patterns with *why* they fail
3. **Reconcile conflicts** — when sources disagree (e.g. agis 50-char subject vs conventional `type(scope):`), document **both** and state catalog/project precedence (`AGENTS.md`, `conventional-commit.py`).
4. Stop Phase 1 only when you can answer: *"What would a reviewer reject, and how would I probe it?"*

## Phase 2 — Note the learning

Write `references/<topic>-learning-note.md`:

| Section | Content |
|---|---|
| Sources | URLs, license, what each contributed |
| Mental model | 1–3 paragraphs — the idea, not a checklist |
| Decision tables | When X → do Y (with examples) |
| Edge cases | From source FAQ / experience |
| Anti-patterns | Named failure modes |
| Skill trace | Which SKILL.md + capsules this note feeds |

The learning note is the **audit trail**. Capsules are the **porter-facing** distillation.

## Phase 3 — Turn into skill material

1. **Capsules** — one or more `references/<topic>-*.md` files in `<!-- capsule-v2 -->` form (question, flow, invariant, probe). Split by seam when one file would exceed ~600 words or mix unrelated invariants.
2. **Skill wiring** — update or create the **application** skill (e.g. `git-workflow-and-versioning` applies Git learning; do not duplicate workflow gates).
3. **Index** — mark row `deep`, link learning note + capsules + application skill.
4. **Router** — one line in `coding-best-practices/references/topic-index.md` when applicable.
5. **Gate** — `SKILLS_ROOT="$PWD/skills" python3 scripts/skill-validator.py` exit 0.

## Red flags (lazy ingestion)

- Capsule exists but no learning note.
- Bullets with no invariant or probe.
- Single pass over README link text without opening primary sources.
- One mega-file mixing Git + semver + changelog.
- Skill that only restates the capsule — application skill must say *when/how to run checks*.

## Verification

- Learning note path exists and lists all primary sources opened.
- Each capsule has `Flow`, `Invariant`, and `Probe` (or explicit "no automated probe — human review").
- Application skill References section links learning note + capsules.
- `ingestion-index` row status = `deep`.
