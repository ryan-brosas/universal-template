---
name: praisonai-foundation
description: Use when porting PraisonAI agent-runtime machinery — LLM completion recovery ladders (classify → compress-context / fallback-model chain / bounded backoff), hard cost-budget guards, fail-closed BEFORE_LLM hook gates, streaming-first fallback routing that never double-executes tools, tool retry policies with denial-key short-circuits and non-idempotent guards, per-agent-instance circuit breakers with GC finalizers, hash-keyed tool-loop detectors, and guardrail regeneration with fail-closed LLM judges.
kind: foundation
invocation: manual
disable-model-invocation: true
---
# praisonai: Agent chat-and-tool-execution kernel

## Foundation contract

This is a cold, source-specific foundation, not an operational procedure. It is
historical, revision-pinned evidence rather than timeless guidance. Current
project source, tests, requirements, and runtime behavior outrank this
projection and decide what ships.

## Provenance and revision

- Source record: `praisonai`; portable upstream identity, license, coverage caveats, and retrieval history are preserved in the index.
- Recorded revision: `main@d82364ec23a83fd9a6e2e849a5285442b4734ca3`.
- Full provenance, coverage caveats, boundaries, and preserved evidence:
  `references/index.md`.

## Topic map

- Representative topics: Completion recovery ladder; Budget guard; BEFORELLM
  hook gate; Streaming fallback routing; Tool retry ladder; Circuit-breaker
  scoping; Loop detection; Guardrail regen + fail-closed judge.
- Scope and retrieval questions: `references/index.md#use-this-for`.
- Complete capsule chooser: `references/index.md#load-the-matching-source-dump`.
- Detailed grouped map: `references/index.md#capsule-map`.
- Source limitations and portability boundaries: `references/index.md#boundaries`.

## Retrieval

Open the index, choose one capsule matching the active question, and load only
that capsule. Revalidate its cited source and revision before relying on it. Do
not bulk-load the inventory, treat historical claims as current truth, or apply
this foundation as a procedure.
