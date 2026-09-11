---
name: linkedin-scrapers-foundation
description: "Use when building or repairing a LinkedIn scraper, Sales Navigator harvester, or Easy Apply bot — cross-repo patterns mined from 13 LinkedIn scraper/bot repos into ONE suite foundation: session/auth handling, rate-limit evasion and detection, pagination and lazy-load walking, profile/job data normalization, application-form automation, and run-level orchestration with crash-safe logging."
kind: foundation
invocation: manual
disable-model-invocation: true
---
# linkedin-scrapers-combined: LinkedIn scraping & Easy Apply automation patterns

## Foundation contract

This is a cold, source-specific foundation, not an operational procedure. It is
historical, revision-pinned evidence rather than timeless guidance. Current
project source, tests, requirements, and runtime behavior outrank this
projection and decide what ships.

## Provenance and revision

- Source record: `linkedin-scrapers`; portable upstream identity, license, coverage caveats, and retrieval history are preserved in the index.
- Recorded revision: `main@0ca5550`.
- Full provenance, coverage caveats, boundaries, and preserved evidence:
  `references/index.md`.

## Topic map

- Representative topics: Session & transport; Browser ops (Puppeteer flavor);
  CDP browser kernel (zendriver, patterns only); Profile parse discipline
  (Puppeteer); Evasion & throttling; Navigation & readiness (linvo); Data
  acquisition; API pagination primitives.
- Scope and retrieval questions: `references/index.md#use-this-for`.
- Complete capsule chooser: `references/index.md#load-the-matching-source-dump`.
- Detailed grouped map: `references/index.md#capsule-map`.
- Source limitations and portability boundaries: `references/index.md#boundaries`.

## Retrieval

Open the index, choose one capsule matching the active question, and load only
that capsule. Revalidate its cited source and revision before relying on it. Do
not bulk-load the inventory, treat historical claims as current truth, or apply
this foundation as a procedure.
