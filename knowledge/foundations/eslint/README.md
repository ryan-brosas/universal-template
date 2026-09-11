---
name: eslint-foundation
description: "Use when building a lint rule engine or flat-config linter: the verify pipeline, config loading/validation and schema-driven cross-config merge algebra, worker-scaled file discovery, RuleTester harness, AST rule primitives, the code-path-analysis kernel, TokenStore cursor/location-index algebra, offset⇄line-column conversion, the verify-tail suppression split, the one-shot engine-bundle constructor with raw-options-vs-module-URL worker transport, fail-loud results-instance binding, the single run-tail result-cache reconcile, the typed warning-service dedup plane with worker-side channel muting, and the default-config lazy rules proxy."
kind: foundation
invocation: manual
disable-model-invocation: true
---
# ESLint Foundation

## Foundation contract

This is a cold, source-specific foundation, not an operational procedure. It is
historical, revision-pinned evidence rather than timeless guidance. Current
project source, tests, requirements, and runtime behavior outrank this
projection and decide what ships.

## Provenance and revision

- Source record: `eslint`; portable upstream identity, license, coverage caveats, and retrieval history are preserved in the index.
- Recorded revision: `main@c27bc926e496985eb7911c09eb60914b2e4b5d0f`.
- Full provenance, coverage caveats, boundaries, and preserved evidence:
  `references/index.md`.

## Topic map

- Representative topics: Verify pipeline; Autofix; Rule execution; Inline
  configuration; Suppression; Config model; Config loading; File discovery &
  scaling.
- Scope and retrieval questions: `references/index.md#use-this-for`.
- Complete capsule chooser: `references/index.md#load-the-matching-source-dump`.
- Detailed grouped map: `references/index.md#capsule-map`.
- Source limitations and portability boundaries: `references/index.md#boundaries`.

## Retrieval

Open the index, choose one capsule matching the active question, and load only
that capsule. Revalidate its cited source and revision before relying on it. Do
not bulk-load the inventory, treat historical claims as current truth, or apply
this foundation as a procedure.
