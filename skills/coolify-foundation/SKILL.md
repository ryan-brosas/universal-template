---
name: coolify-foundation
description: "Use when porting a self-hosted deploy orchestrator (Coolify, PaaS-style) — a DB-backed deployment queue with admission control, a 5k-line build-pack state machine that drives remote Docker hosts over SSH, rolling updates with health-gated cutover, and cron-dedup scheduled jobs. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval."
kind: foundation
invocation: manual
disable-model-invocation: true
---
# Coolify: Self-hosted deploy orchestrator foundation

## Foundation contract

This is a cold, source-specific foundation, not an operational procedure. It is
historical, revision-pinned evidence rather than timeless guidance. Current
project source, tests, requirements, and runtime behavior outrank this
projection and decide what ships.

## Provenance and revision

- Source record: `coolify`; portable upstream identity, license, coverage caveats, and retrieval history are preserved in the index.
- Recorded revision: `main@981163973b4b33726e378d7dcf9812459efc6f60`.
- Full provenance, coverage caveats, boundaries, and preserved evidence:
  `references/index.md`.

## Topic map

- Representative topics: Deployment queue admission; Status state machine;
  Build-pack router; Env var pipeline; Rolling update; Container cleanup;
  Remote command lifecycle; SSH multiplexing.
- Scope and retrieval questions: `references/index.md#use-this-for`.
- Complete capsule chooser: `references/index.md#load-the-matching-source-dump`.
- Detailed grouped map: `references/index.md#capsule-map`.
- Source limitations and portability boundaries: `references/index.md#boundaries`.

## Retrieval

Open the index, choose one capsule matching the active question, and load only
that capsule. Revalidate its cited source and revision before relying on it. Do
not bulk-load the inventory, treat historical claims as current truth, or apply
this foundation as a procedure.
