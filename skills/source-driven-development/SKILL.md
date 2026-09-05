---
name: source-driven-development
description: "Use when an implementation depends on unfamiliar library, API, or framework behavior; verify the relevant version and behavioral claim from authoritative evidence."
invocation: internal
disable-model-invocation: true
---

# Verify an external behavior

Use the installed version's source, docs or a direct probe for the unfamiliar
behavior the change actually depends on. Current local tests and implementation
outrank a remembered API or a historical capsule. State material uncertainty
when evidence is unavailable rather than inventing a flag, import or guarantee.

Useful shortcuts:

- A capsule's file path and exact revision can take you straight to upstream
  source. Capsules in one foundation may describe different revisions; the
  selected capsule's pin matters more than the index's headline revision.
- Pin raw-file URLs used as evidence to the relevant commit SHA; resolve a
  release tag to its commit when needed. Moving branches can help discovery but
  are not reproducible citations. A direct fetch or installed source read usually
  needs no checkout, code index, model resolver or research workflow. Save a
  fetched file when several reads will use it instead of downloading it again.
- A small behavioral probe can settle semantics that docs leave ambiguous.
  Check the real boundary, not just a mock that restates the assumption.
- Copy source links exactly. A correct implementation with an invented citation
  path is still a misleading report.

Cite the evidence that carries the consequential claim and distinguish it from
inference. `../evidence-router/SKILL.md` is an optional capability map when you
do not know where to look, not a prerequisite before using a known source.
