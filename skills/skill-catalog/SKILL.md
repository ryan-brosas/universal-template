---
name: skill-catalog
description: "Use when the user asks what skills exist, when finding the right skill for a topic, or during non-trivial implementation when a cheap check for relevant hidden skills or foundations would reduce uncertainty - deterministic metadata search; load only selected matches."
---

# Skill Catalog

## Core Principle

**Search broadly. Load narrowly.** Discovery is a deterministic metadata query,
not a model memory test. Hidden skills and foundation-pack leaves stay out of
startup context but remain cheap to find on demand. Search returns scored
candidates; read only the few that materially help.

## When to Use / NOT

- **User-facing catalog search:** "what skills do we have?", "find a skill for
 CI", "show GitHub skills".
- **Internal relevance discovery:** during non-trivial implementation, after
 grounding in the current project (and any project-local `reference/` assets),
 run one cheap metadata lookup before reinventing patterns:
 `python3 scripts/skill-catalog.py search-leverage "<task concepts>" --limit 5`.
- **Foundation-only lookup:** `python3 scripts/skill-catalog.py
 search-foundations "<stack or pattern>" --limit 8`.
- **NOT when:** a trivial/local edit and current project source already answer
 the question.
- **NOT when:** a visible skill already matches directly, invoke that skill.
- **NOT when:** choosing evidence sources or execution shape, `evidence-router`
 and `execution-router` own those decisions.

## Workflow

1. **Cheap discovery (non-trivial work):**
 `python3 scripts/skill-catalog.py search-leverage "<concepts>" --limit 5`
 returns scored skill and foundation candidates (metadata only).
2. **Skill-only or foundation-only** when the need is obvious:
 `search "<topic>"` or `search-foundations "<topic>"`.
3. **Inspect before loading:** `python3 scripts/skill-catalog.py show <name>`
 for one skill's class, visibility, path, and related skills.
4. **Load narrowly:** open only the chosen `skills/<name>/SKILL.md` or
 `foundation-pack/<name>/SKILL.md`; follow foundation source pointers to real
 code when implementation details matter.
5. After catalog edits: `python3 scripts/skill-catalog.py generate` refreshes
 the human catalog; CI fails on stale generated docs.

## Red Flags

- Pasting the catalog or every match into context instead of returning candidates.
- Loading every candidate that matched; read the best one first, stop when enough.
- Hand-editing `docs/skill-catalog.md`, it is generated from skill metadata.
- Skipping discovery on non-trivial work because the user did not say "check
 foundation-pack" or "find a skill".
- Treating discovery timing as authority priority; project source and project-local
 references still outrank generic skills and foundations.

## Verification

- `python3 scripts/skill-catalog.py stats` exits 0 with counts.
- `python3 scripts/skill-catalog.py generate --check` exits 0 after regeneration.
- `python3 scripts/skill-catalog.py --selftest` passes ranked fixture discovery.

## References

- `scripts/skill-catalog.py`, list / search / search-foundations /
 search-leverage / show / stats / generate.
- `foundation-pack/`, accumulated implementation foundations; metadata search
 via `search-foundations` or `search-leverage`, not startup metadata.
- `docs/skill-catalog.md`, generated human catalog (skills only; foundations
 stay outside the active catalog by design).
