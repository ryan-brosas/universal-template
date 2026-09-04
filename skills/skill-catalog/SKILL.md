---
name: skill-catalog
description: "Use when the user asks what skills exist or needs to find the right skill for a topic; inspect local frontmatter and return only relevant candidates."
invocation: entry
---

# Skill Catalog

## Core Principle

The filesystem and each `SKILL.md` frontmatter are the catalog. Native host
skill discovery, file search, and repository search are sufficient. Generated
views are optional human conveniences.

## When to Use / NOT

- **Use when:** the user asks what skills exist, requests a skill for a topic,
  or this repository's catalog is being maintained.
- **NOT when:** a visible skill already matches directly, or ordinary project
  source answers the task.

## Workflow

1. List bounded candidates under `skills/*/SKILL.md` with native filesystem or
   repository search.
2. Read candidate `name`, `description`, `invocation`, and
   `disable-model-invocation` frontmatter.
3. Judge fit from the request and overlap with neighboring candidates. Load only
   the best match and any references it names.
4. For catalog maintenance, update metadata in the owning skill. Regenerate
   `docs/skill-catalog.md` only because it is retained for human browsing.

`scripts/skill-catalog.py` remains optional generated-artifact tooling. It is not
an ordinary cognitive route or a source of classification truth.

## Red Flags

- Loading the complete catalog into context.
- Treating scored string matches as a routing decision.
- Editing the generated catalog instead of skill frontmatter.
- Centralizing skill names in another inventory.

## Verification

Direct inspection finds the skill and its metadata. For publication, the
relevant exact metadata validator and generated-parity check in
`CONTRIBUTING.md` pass.

## References

- `../../docs/skill-catalog.md`, optional generated human view.
- `../../scripts/skill-catalog.py`, optional list/search/generate helper.
