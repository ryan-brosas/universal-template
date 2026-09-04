---
name: quickbeam-foundation
description: "Use when porting embedded JS execution sandboxes on the BEAM (QuickJS/duktape-style engines in Elixir/Erlang), GenServer↔NIF async ref protocols, runtime/context pools with reset-on-checkin, bytecode verify-pin-evaluate pipelines with hard resource limits, optional JIT tiers over untrusted input (single-flight compile caches, validated deopt, stack dataflow verification), or TS bundler resolution ladders."
kind: foundation
invocation: manual
disable-model-invocation: true
---
# QuickBEAM: JavaScript-runtime-on-the-BEAM foundations

## Foundation contract

This is a cold, source-specific foundation, not an operational procedure. It is
historical, revision-pinned evidence rather than timeless guidance. Current
project source, tests, requirements, and runtime behavior outrank this
projection and decide what ships.

## Provenance and revision

- Source record: `quickbeam`; portable upstream identity, license, coverage caveats, and retrieval history are preserved in the index.
- Recorded revision: `master@c21c0e315213d0801950aae48cccedb3051c32d8`.
- Full provenance, coverage caveats, boundaries, and preserved evidence:
  `references/index.md`.

## Topic map

- Representative topics: Runtime spine; Pool planes; Context lifecycle;
  Isolated VM subsystem; Invocation & exception protocol; Value, property &
  heap plane; Engine orchestration & measurement plane; Web API plane.
- Scope and retrieval questions: `references/index.md#use-this-for`.
- Complete capsule chooser: `references/index.md#load-the-matching-source-dump`.
- Detailed grouped map: `references/index.md#capsule-map`.
- Source limitations and portability boundaries: `references/index.md#boundaries`.

## Retrieval

Open the index, choose one capsule matching the active question, and load only
that capsule. Revalidate its cited source and revision before relying on it. Do
not bulk-load the inventory, treat historical claims as current truth, or apply
this foundation as a procedure.
