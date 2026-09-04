---
name: codedb-foundation
description: "Use when building or porting codedb-style code-intelligence search engines — typo-substring trigram indexes with bloom pruning, inverted word indexes with BM25+ ranking, content-defined n-gram indexes, mmap zero-copy persistence, deterministic call/import graphs, generation-safe result caches, and tiered recall ladders for agent context tools. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval."
kind: foundation
invocation: manual
disable-model-invocation: true
---
# codedb: Code-Intelligence Search Engine Foundation

## Foundation contract

This is a cold, source-specific foundation, not an operational procedure. It is
historical, revision-pinned evidence rather than timeless guidance. Current
project source, tests, requirements, and runtime behavior outrank this
projection and decide what ships.

## Provenance and revision

- Source record: `codedb`; portable upstream identity, license, coverage caveats, and retrieval history are preserved in the index.
- Recorded revision: `main@43bc3ca2`.
- Full provenance, coverage caveats, boundaries, and preserved evidence:
  `references/index.md`.

## Topic map

- Representative topics: Zero-copy word index; Removal dual-path & shard
  parity; Bloom posting masks; Regex prefilter compiler; Sparse n-grams;
  Overlay lattice; Two-file disk format; Tier ladder.
- Scope and retrieval questions: `references/index.md#use-this-for`.
- Complete capsule chooser: `references/index.md#load-the-matching-source-dump`.
- Detailed grouped map: `references/index.md#capsule-map`.
- Source limitations and portability boundaries: `references/index.md#boundaries`.

## Retrieval

Open the index, choose one capsule matching the active question, and load only
that capsule. Revalidate its cited source and revision before relying on it. Do
not bulk-load the inventory, treat historical claims as current truth, or apply
this foundation as a procedure.
