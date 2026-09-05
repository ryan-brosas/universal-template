---
name: skill-catalog
description: "Use when finding a skill, or when a specialized tool, platform, or delivery task has no clear hot owner; search the cold catalog before inventing a replacement workflow. Not a mandatory step for ordinary tasks."
invocation: entry
---

# Skill Catalog

The filesystem and skill frontmatter are canonical; generated catalogs are human
browsing aids. Skip discovery when a visible skill clearly owns the request or
ordinary project source is enough.

Search bounded filenames and descriptions for the active question. Inspect the
best candidates’ name, description, kind, invocation, and hidden flag; choose one
operational owner. For legitimate overlap, follow stated precedence rather than
loading every candidate. Hidden/manual skills remain usable through explicit
requests, prompts, project instructions, or this search.

For a foundation, inspect its compact topic map, search reference filenames and
headings, then open 1–3 likely capsules. Read the full index only when discovery
remains ambiguous; it is an inventory, not a mandatory context load.

For maintenance, change the owning frontmatter and regenerate the retained
operational/foundation catalogs. Promote nothing automatically. Hot exposure needs
recurring use, reliable selection, and distinct demonstrated lift. Missing usage
telemetry is unknown, not proof that a skill is unused. Keep meaning and promotion
decisions with the model; scripts validate metadata and disjoint surfaces.

## Verification

Check explicit callers and host visibility after metadata changes. Run the target
checkout’s applicable publication checks; do not run template scripts in an
unrelated project. `../../scripts/skill-catalog.py` provides optional list, search,
context, invocation-size, and generated-view diagnostics. Use `invocation <name>`
for one loader or `invocation --limit 10` for the largest tracked loaders; these
are optional inventories, not runtime-cost measurements or publication limits.
