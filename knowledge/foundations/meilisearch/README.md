---
name: meilisearch-foundation
description: Use when porting or debugging typo-tolerant full-text search internals — query-term derivation, query-graph construction, graph-based ranking rules, bucket execution, posting-list caching, or phrase resolution from meilisearch/milli.
kind: foundation
invocation: manual
disable-model-invocation: true
---
# Meilisearch (milli): typo-tolerant search engine foundation

## Foundation contract

This is a cold, source-specific foundation, not an operational procedure. It is
historical, revision-pinned evidence rather than timeless guidance. Current
project source, tests, requirements, and runtime behavior outrank this
projection and decide what ships.

## Provenance and revision

- Source record: `meilisearch`; portable upstream identity, license, coverage caveats, and retrieval history are preserved in the index.
- Recorded revision: `main@577f7af28942b71782eab1e59f44ad8296ce0a92`.
- Full provenance, coverage caveats, boundaries, and preserved evidence:
  `references/index.md`.

## Topic map

- Representative topics: Typo tolerance; Query understanding; Ranking rules;
  Execution; Phrase & attributes; Facet levels & filtering (pass 2).
- Scope and retrieval questions: `references/index.md#use-this-for`.
- Complete capsule chooser: `references/index.md#load-the-matching-source-dump`.
- Detailed grouped map: `references/index.md#capsule-map`.
- Source limitations and portability boundaries: `references/index.md#boundaries`.

## Retrieval

Open the index, choose one capsule matching the active question, and load only
that capsule. Revalidate its cited source and revision before relying on it. Do
not bulk-load the inventory, treat historical claims as current truth, or apply
this foundation as a procedure.
