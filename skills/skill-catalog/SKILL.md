---
name: skill-catalog
description: "Use when the user asks what skills exist or needs to find the right skill for a topic - deterministic search over the local catalog; return candidates and load only the chosen skill."
---

# Skill Catalog

## Core Principle

This skill is for **explicit catalog queries and ~/.agents maintenance**, not
for ordinary coding work in another repository. Search returns scored
candidates; load only the chosen skill. Hidden specialists stay out of startup
metadata but remain available through host skill discovery.

## When to Use / NOT

- **Use when:** "what skills do we have?", "find a skill for CI", "show GitHub
 skills", or maintaining the catalog in `~/.agents`.
- **NOT when:** implementing in an arbitrary project repository. Use host skill
 discovery, read relevant `SKILL.md` files directly, and reason about fit.
- **NOT when:** a visible skill already matches the request directly, invoke
 that skill.
- **NOT when:** choosing evidence sources or execution shape, `evidence-router`
 and `execution-router` own those decisions.

Foundations live in `foundation-pack/`, outside this catalog. Inspect them with
host filesystem or search capabilities when they may help; do not route through
this script during normal project work.

## Workflow (catalog maintenance only)

When working on `~/.agents` or answering an explicit catalog question:

1. `python3 scripts/skill-catalog.py search "<topic>" --limit 8`
2. Narrow when useful: `list --visible`, `list --hidden`, `list --class cold`.
3. `python3 scripts/skill-catalog.py show <name>` before loading.
4. Load only the chosen candidate (`skills/<name>/SKILL.md`).
5. After catalog edits: `python3 scripts/skill-catalog.py generate`

## Red Flags

- Invoking catalog scripts during ordinary project implementation elsewhere.
- Pasting the catalog into context instead of returning a few candidates.
- Loading every candidate that matched.
- Hand-editing `docs/skill-catalog.md`.

## Verification

- `python3 scripts/skill-catalog.py stats` exits 0.
- `python3 scripts/skill-catalog.py generate --check` exits 0 after regeneration.

## References

- `scripts/skill-catalog.py`, list / search / show / stats / generate.
- `foundation-pack/`, accumulated implementation foundations; inspect directly.
- `docs/skill-catalog.md`, generated human catalog.
