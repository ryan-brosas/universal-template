---
name: skill-catalog
description: "Use when the user asks what skills exist, to find a skill for a topic, or to surface cold or foundation knowledge - deterministic search over the local catalog; return candidates and load only the chosen skill."
---

# Skill Catalog

## Core Principle

Discovery is a deterministic filesystem query, not a model memory test. Search
the catalog, show a few scored candidates with their class, then load only the
chosen skill. The catalog is large by design (foundations and specialists stay
hidden); visible startup metadata stays small.

## When to Use / NOT

- **Use when:** "what skills do we have?", "find a skill for CI", "do we have a
  Django foundation?", "show GitHub skills", "list cold foundations".
- **Use when:** a hidden or cold capability is suspected and startup metadata
  does not show it.
- **NOT when:** a visible skill already matches the request directly — invoke
  that skill.
- **NOT when:** choosing evidence sources or execution shape — `evidence-router`
  and `execution-router` own those decisions.

## Workflow

1. `python3 scripts/skill-catalog.py search "<topic>" --limit 8` — scored
   candidates with class and visibility.
2. Narrow when useful: `list --visible`, `list --hidden`, `list --foundations`,
   `list --class cold`, `list --category github`.
3. Inspect before loading: `python3 scripts/skill-catalog.py show <name>`
   (description, class, model-visible, path, related skills).
4. Load only the chosen candidate (`skills/<name>/SKILL.md`) and proceed.
5. After catalog edits: `python3 scripts/skill-catalog.py generate` refreshes
   the human catalogs; CI fails on stale generated docs.

## Red Flags

- Pasting the catalog into the answer instead of returning candidates.
- Loading every foundation that matched — read the best candidate first.
- Hand-editing `docs/skill-catalog.md` or `docs/foundation-catalog.md` — both
  are generated files.
- Adding a visible skill without classifying it (catalog-quality fails the
  build until it lands in ENTRY_SKILLS, ROUTER_SKILLS, or VENDOR_SKILLS).

## Verification

- `python3 scripts/skill-catalog.py stats` exits 0 with counts.
- `python3 scripts/skill-catalog.py generate --check` exits 0 after
  regeneration.

## References

- `scripts/skill-catalog.py` — deterministic catalog tool (list, search, show,
  stats, generate).
- `scripts/foundation-search.py` — foundation-only ranked search (cold
  fallback).
- `docs/skill-catalog.md` and `docs/foundation-catalog.md` — generated human
  catalogs.
