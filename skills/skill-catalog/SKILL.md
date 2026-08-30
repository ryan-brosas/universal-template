---
name: skill-catalog
description: "Use when the user asks what skills exist or needs to find the right skill for a topic - deterministic search over the local catalog; return candidates and load only the chosen skill."
---

# Skill Catalog

## Core Principle

Discovery is a deterministic filesystem query, not a model memory test. Search
the catalog, show a few scored candidates with their class, then load only the
chosen skill. The catalog is large by design (specialists stay hidden); visible
startup metadata stays small.

## When to Use / NOT

- **Use when:** "what skills do we have?", "find a skill for CI", "show GitHub
  skills".
- **Use when:** a hidden or cold capability is suspected and startup metadata
  does not show it.
- **Use when:** the user asks to search the cold legacy foundation pack —
  plain `grep -ril "<topic>" foundation-pack/` is enough (the pack is not
  part of the active catalog).
- **NOT when:** a visible skill already matches the request directly — invoke
  that skill.
- **NOT when:** choosing evidence sources or execution shape — `evidence-router`
  and `execution-router` own those decisions.

## Workflow

1. `python3 scripts/skill-catalog.py search "<topic>" --limit 8` — scored
   candidates with class and visibility.
2. Narrow when useful: `list --visible`, `list --hidden`, `list --class cold`.
3. Inspect before loading: `python3 scripts/skill-catalog.py show <name>`
   (description, class, model-visible, path, related skills).
4. Load only the chosen candidate (`skills/<name>/SKILL.md`) and proceed.
5. After catalog edits: `python3 scripts/skill-catalog.py generate` refreshes
   the human catalog; CI fails on stale generated docs.

## Red Flags

- Pasting the catalog into the answer instead of returning candidates.
- Loading every candidate that matched — read the best one first.
- Hand-editing `docs/skill-catalog.md` — it is generated from
  `skills/*/SKILL.md` metadata.
- Adding a visible skill without classifying it (catalog-quality fails the
  build until it lands in ENTRY_SKILLS, ROUTER_SKILLS, or VENDOR_SKILLS).

## Verification

- `python3 scripts/skill-catalog.py stats` exits 0 with counts.
- `python3 scripts/skill-catalog.py generate --check` exits 0 after
  regeneration.

## References

- `scripts/skill-catalog.py` — deterministic catalog tool (list, search, show,
  stats, generate).
- `foundation-pack/` — cold legacy capsules; search with plain `grep`,
  not the catalog.
- `docs/skill-catalog.md` — generated human catalog.
