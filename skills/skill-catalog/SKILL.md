---
name: skill-catalog
description: "Use when useful expertise is missing from the visible skills, a task could benefit from a source-specific foundation, or the user asks what capabilities exist. Discover cold context with native file search; no catalog command required."
invocation: entry
---

# Find useful context

The filesystem and skill frontmatter are canonical; generated catalogs are human
browsing aids. The canonical tree is this directory's parent (`../`), including
cold capabilities omitted from the host's startup list. Skip discovery when a
visible skill clearly owns the request or ordinary project source is enough.

Search bounded filenames and descriptions for the active question. From the
skill-tree root, `rg -l --glob SKILL.md 'migration|codemod' .` is one possible
candidate search, not a scoring system or required command. Inspect plausible
candidates' name, description, kind, invocation and visibility, then load what
helps. Combine matches for distinct needs, not every overlapping procedure.
Hidden/manual skills remain usable through explicit requests, prompts, project
instructions or this search. No Python, generated inventory or model resolver
is required; a search miss does not require building a new inventory.

For a foundation, inspect its compact topic map, search reference filenames and
headings, then open the likely capsules. Use the index only when discovery
remains ambiguous; it is an inventory, not a mandatory context load. Check each
selected capsule's own revision, limits and source links. A remembered graph
project or tool name is a retrieval hint, not a required integration.

For maintenance, change the owning frontmatter and regenerate the retained
operational/foundation catalogs. Promote nothing automatically. Hot exposure needs
recurring use, reliable selection, and distinct demonstrated lift. Missing usage
telemetry is unknown, not proof that a skill is unused. Keep meaning and promotion
decisions with the model; scripts validate metadata and disjoint surfaces.
Hiding a description does not necessarily prevent the host from scanning its body.

## Verification

Check explicit callers and host visibility after metadata changes. Run the target
checkout's applicable publication checks; do not run template scripts in an
unrelated project. `../../scripts/skill-catalog.py` provides optional list, search,
context, invocation-size and generated-view diagnostics. `invocation <name>`
inspects one loader; `invocation --limit 10` lists the largest tracked loaders.
These are optional inventories, not runtime-cost measurements or publication
limits. The model owns the approach, not these diagnostic commands.
