---
name: ollama-foundation
description: "Use when porting local model-serving machinery from Ollama: scheduler load/evict loops, VRAM prediction and GPU placement, OOM retry ladders, streaming NDJSON→SSE codecs, thinking/harmony/tool parsers, capability derivation, and OpenAI/Anthropic compat bridges."
kind: foundation
invocation: manual
disable-model-invocation: true
---
# Ollama: local model server foundation

## Foundation contract

This is a cold, source-specific foundation, not an operational procedure. It is
historical, revision-pinned evidence rather than timeless guidance. Current
project source, tests, requirements, and runtime behavior outrank this
projection and decide what ships.

## Provenance and revision

- Source record: `ollama`; portable upstream identity, license, coverage caveats, and retrieval history are preserved in the index.
- Recorded revision: `main@fb30760996871fa9460115c753afd2c60d4ab0f7`.
- Full provenance, coverage caveats, boundaries, and preserved evidence:
  `references/index.md`.

## Topic map

- Representative topics: Scheduling kernel; Runner identity; OOM recovery; GPU
  placement; Batch sizing; VRAM convergence; Reload decision; Chat mode
  duality.
- Scope and retrieval questions: `references/index.md#use-this-for`.
- Complete capsule chooser: `references/index.md#load-the-matching-source-dump`.
- Detailed grouped map: `references/index.md#capsule-map`.
- Source limitations and portability boundaries: `references/index.md#boundaries`.

## Retrieval

Open the index, choose one capsule matching the active question, and load only
that capsule. Revalidate its cited source and revision before relying on it. Do
not bulk-load the inventory, treat historical claims as current truth, or apply
this foundation as a procedure.
