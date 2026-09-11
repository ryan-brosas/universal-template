---
name: requests-foundation
description: "Use when porting psf/requests internals — session orchestration, transport adapter/pool plane, redirect/auth/proxy state machines, prepared-request pipeline, and response consumption contracts."
kind: foundation
invocation: manual
disable-model-invocation: true
---
# requests: Foundation

## Foundation contract

This is a cold, source-specific foundation, not an operational procedure. It is
historical, revision-pinned evidence rather than timeless guidance. Current
project source, tests, requirements, and runtime behavior outrank this
projection and decide what ships.

## Provenance and revision

- Source record: `requests`; portable upstream identity, license, coverage caveats, and retrieval history are preserved in the index.
- Recorded revision: `main@8f8b212de8c2129d7954c6cd373762880375620a`.
- Full provenance, coverage caveats, boundaries, and preserved evidence:
  `references/index.md`.

## Topic map

- Representative topics: Session settings; Adapter dispatch; Redirect loop;
  Auth stripping; Method rewrite; Proxy rebuild; Env settings; Send pipeline.
- Scope and retrieval questions: `references/index.md#use-this-for`.
- Complete capsule chooser: `references/index.md#load-the-matching-source-dump`.
- Detailed grouped map: `references/index.md#capsule-map`.
- Source limitations and portability boundaries: `references/index.md#boundaries`.

## Retrieval

Open the index, choose one capsule matching the active question, and load only
that capsule. Revalidate its cited source and revision before relying on it. Do
not bulk-load the inventory, treat historical claims as current truth, or apply
this foundation as a procedure.
