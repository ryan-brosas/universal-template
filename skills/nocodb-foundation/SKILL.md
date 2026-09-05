---
name: nocodb-foundation
description: "Use when building job-queue systems, background/migration jobs, DB-backed caches, streaming data import/export, cross-instance schema serialization with id remapping, or file lifecycle jobs — plus record CRUD funnels (single/bulk), the v1/v2 alias data entry with its shared list engine and nested-link query sanitization, LTAR link engines (nested dispatch, copy/paste swap, display-value linking, cross-base contexts), meta-sync diff/apply machinery (splice diff, pk ratchet, m2m promotion), anonymous shared-view/form security gates AND shared-view metadata projection (related-metas fixpoint, secret stripping), OR pg formula compilation with Airtable IEEE semantics (x/0→±Infinity/NaN CASE ladders, blank→0 coalescing, NaN sort-rank agreement, string-token wire contract) AND drift-hardening seams (per-level nested-lookup link conditions, V2-link conversion guards, import display-value admission): Bull-compatible fallback queue AND Redis variant, versioned migration jobs (incl. EE/CE skew), worker/primary…"
kind: foundation
invocation: manual
disable-model-invocation: true
---
# NocoDB Foundation

## Foundation contract

This is a cold, source-specific foundation, not an operational procedure. It is
historical, revision-pinned evidence rather than timeless guidance. Current
project source, tests, requirements, and runtime behavior outrank this
projection and decide what ships.

## Provenance and revision

- Source record: `nocodb`; portable upstream identity, license, coverage caveats, and retrieval history are preserved in the index.
- Recorded revision: `develop@640fe3b06fb26c9d000e2258477001c0d5e62c73`.
- Full provenance, coverage caveats, boundaries, and preserved evidence:
  `references/index.md`.

## Topic map

- Representative topics: Queue core; Worker admission; Enqueue contract; Event
  fan-out; Long-poll surface; Versioned migrations; Cache safety; Redis queue.
- Airtable LongText / PostgreSQL NUL (U+0000) removal, per-field coercion and
  SingleSelect quirks: `references/import-record-coercion-ladder.md`.
- Scope and retrieval questions: `references/index.md#use-this-for`.
- Complete capsule chooser: `references/index.md#load-the-matching-source-dump`.
- Detailed grouped map: `references/index.md#capsule-map`.
- Source limitations and portability boundaries: `references/index.md#boundaries`.

## Retrieval

Choose a capsule from the topic map or index and load only the matching evidence.
Capsules span revisions; use the selected capsule’s own file and pin, not the
headline revision above. Revalidate that source before relying on it. Do
not bulk-load the inventory, treat historical claims as current truth, or apply
this foundation as a procedure.
