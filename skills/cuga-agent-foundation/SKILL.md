---
name: cuga-agent-foundation
description: "Use when building LangGraph policy layers for agents: intent guards, playbooks, tool guides, tool approval HITL, output formatters, ToolGuard runtime enforcement plus its build-time code generation, policy storage/sync, agent-state reducers, decision observability, and the shared agent-loop kernel (CoreGraphAdapter, call_model routing, fenced-code extraction, approval interrupt/resume, execution-backend resolution, runtime tool injection), plus the provider-dialect structured-output chain factory, the three-tier tool-call budget, and the code-execution plane (unified charging entry, timeout/exit evidence recovery, two-tier AST security, JSON-safe variable capture, monotonic-safe clock freeze, remote sandbox transport, shell workspace isolation, sandbox session caching) — plus the platform-infra plane: total-context-aware summarization with hard-truncation fallback, slash-command soft dispatch with four-pass arg substitution, never-raise secret resolution/seeding, multi-issuer JWT/IAM validation, hybrid RAG…"
kind: foundation
invocation: manual
disable-model-invocation: true
---
# Cuga Agent Foundation

## Foundation contract

This is a cold, source-specific foundation, not an operational procedure. It is
historical, revision-pinned evidence rather than timeless guidance. Current
project source, tests, requirements, and runtime behavior outrank this
projection and decide what ships.

## Provenance and revision

- Source record: `cuga-agent`; portable upstream identity, license, coverage caveats, and retrieval history are preserved in the index.
- Recorded revision: `main@5de53ade77c36166da6ace906af488b2b445454f`.
- Full provenance, coverage caveats, boundaries, and preserved evidence:
  `references/index.md`.

## Topic map

- Representative topics: Policy data model; Config wiring; Matching engine;
  Enactment; Intent blocking; Tool description guides; Human approval; Output
  formatting.
- Scope and retrieval questions: `references/index.md#use-this-for`.
- Complete capsule chooser: `references/index.md#load-the-matching-source-dump`.
- Detailed grouped map: `references/index.md#capsule-map`.
- Source limitations and portability boundaries: `references/index.md#boundaries`.

## Retrieval

Open the index, choose one capsule matching the active question, and load only
that capsule. Revalidate its cited source and revision before relying on it. Do
not bulk-load the inventory, treat historical claims as current truth, or apply
this foundation as a procedure.
