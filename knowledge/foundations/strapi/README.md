---
name: strapi-foundation
description: Use when porting Strapi's DB-agnostic database kernel — knex-compiling query-builder state machine, lifecycle-hooked write pipeline with compensating rollback, per-subscriber hook-state threading, bounded identifier shortening, N+1-free batch populate, connect-order topological sorting, anyToOne relinking with document-sibling exclusion, hash-gated schema sync with 3-way DDL diffing, constraint-safe alter ladders, exactly-once migration runner, dual-stream user/internal migration providers, row-number deep-sort wrapping with virtual status ranking sort, three-pass metadata loading with preset-name skip, morphOne reverse-link cascade deletes, fixed-order streaming transfer stages with skip/cancel/rollback, stream-replacing progress trackers with pre-start totals, index-difference flow state machines over WebSocket step protocols, uuid dedup-replay idempotent dispatch, and init-echo binary wire negotiation.
kind: foundation
invocation: manual
disable-model-invocation: true
---
# Strapi: database-kernel foundation

## Foundation contract

This is a cold, source-specific foundation, not an operational procedure. It is
historical, revision-pinned evidence rather than timeless guidance. Current
project source, tests, requirements, and runtime behavior outrank this
projection and decide what ships.

## Provenance and revision

- Source record: `strapi`; portable upstream identity, license, coverage caveats, and retrieval history are preserved in the index.
- Recorded revision: `develop@1fd9d80ad5f0a2c97d09ce7529f5cd9fdb91ca2d`.
- Full provenance, coverage caveats, boundaries, and preserved evidence:
  `references/index.md`.

## Topic map

- Representative topics: metadata-load-models; query-builder-knex-compilation;
  status-sort-expression; deep-sort-wrap; entity-manager-write-pipeline;
  lifecycles-provider; identifier-shortener; batch-populate-apply.
- Scope and retrieval questions: `references/index.md#use-this-for`.
- Complete capsule chooser: `references/index.md#load-the-matching-source-dump`.
- Detailed grouped map: `references/index.md#capsule-map`.
- Source limitations and portability boundaries: `references/index.md#boundaries`.

## Retrieval

Open the index, choose one capsule matching the active question, and load only
that capsule. Revalidate its cited source and revision before relying on it. Do
not bulk-load the inventory, treat historical claims as current truth, or apply
this foundation as a procedure.
