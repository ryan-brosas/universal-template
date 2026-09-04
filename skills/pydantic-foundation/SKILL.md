---
name: pydantic-foundation
description: "Use when porting pydantic-v2-style machinery into another codebase: metaclass-driven model class construction, deferred/lazy validator+serializer builds with loud mock errors, generic-model parametrization and caching, union→tagged-union conversion, core-schema traversal/cleaning, or a type-checker plugin that synthesizes fields-aware constructors. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval."

kind: foundation
invocation: manual
disable-model-invocation: true
---
# pydantic: Foundation

## Foundation contract

This is a cold, source-specific foundation, not an operational procedure. It is
historical, revision-pinned evidence rather than timeless guidance. Current
project source, tests, requirements, and runtime behavior outrank this
projection and decide what ships.

## Provenance and revision

- Source record: `pydantic`; portable upstream identity, license, coverage caveats, and retrieval history are preserved in the index.
- Recorded revision: `main@2151025aa51263f3016502b00010b78e4481eaa1`.
- Full provenance, coverage caveats, boundaries, and preserved evidence:
  `references/index.md`.

## Topic map

- Representative topics: Model class construction; Deferred builds; Generics;
  Discriminated unions; Core schema tooling; mypy plugin; Fields & metadata
  plane; Validation execution.
- Scope and retrieval questions: `references/index.md#use-this-for`.
- Complete capsule chooser: `references/index.md#load-the-matching-source-dump`.
- Detailed grouped map: `references/index.md#capsule-map`.
- Source limitations and portability boundaries: `references/index.md#boundaries`.

## Retrieval

Open the index, choose one capsule matching the active question, and load only
that capsule. Revalidate its cited source and revision before relying on it. Do
not bulk-load the inventory, treat historical claims as current truth, or apply
this foundation as a procedure.
