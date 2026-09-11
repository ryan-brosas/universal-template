---
title: source-driven-development
summary: Use when an implementation depends on unfamiliar library, API, or framework behavior; verify the relevant version and behavioral claim from authoritative evidence.
kind: playbook
---

# Verify an external behavior

Use the installed version's source, docs or a direct probe for the unfamiliar
behavior the change actually depends on. Current local tests and implementation
outrank a remembered API or a remembered summary. State material uncertainty
when evidence is unavailable rather than inventing a flag, import or guarantee.

Useful shortcuts:

- Pin what you read: cite the repository, path, and commit or release for the
  behavior you verified, and prefer that source over a remembered API.
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
inference. Pick the nearest sufficient source; global rules own where to look.
