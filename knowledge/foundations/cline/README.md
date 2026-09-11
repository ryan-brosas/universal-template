---
name: cline-foundation
description: "Use when porting Cline's agentic-runtime core — context compaction (trigger budget, overflow-recovery ladder, safe cuts, no-LLM fold), compaction state projection with prefix hashes, runtime safety (loop detection, mistake tracker), pending-prompt steer/queue gate, local hub-daemon transport plane (discovery record, mkdir-lock mutex, ensure/retire ladders, WS envelope, subscription refcounts), claim-once env sentinels with supervised-child restart/adoption, hub command router (authority/drain gates, degraded replies), monotonic shutdown coordination, disk-truth cron reconciliation, agenda task persistence kernel (run-admission gates, exactly-once terminals, crash triage, revision+content-hash CAS), strict/tolerant Markdown intent grammars, location containment, todo-tool scope gate, workspace file-index TTL worker, @mention budget matching, ACP stdio bridge (stdio hygiene, fail-closed permissions, streaming/replay, session lifecycle, config options). Source code and direct tests are ground truth."
kind: foundation
invocation: manual
disable-model-invocation: true
---
# Cline: agentic coding-agent runtime core

## Foundation contract

This is a cold, source-specific foundation, not an operational procedure. It is
historical, revision-pinned evidence rather than timeless guidance. Current
project source, tests, requirements, and runtime behavior outrank this
projection and decide what ships.

## Provenance and revision

- Source record: `cline`; portable upstream identity, license, coverage caveats, and retrieval history are preserved in the index.
- Recorded revision: `main@4f836ae7d0ed29ece7ef4a2a478deb470fdd056e`.
- Full provenance, coverage caveats, boundaries, and preserved evidence:
  `references/index.md`.

## Topic map

- Representative topics: Context compaction
  (sdk/packages/core/src/extensions/context/); Session state
  (src/session/models/); Runtime safety (src/runtime/safety/,
  src/runtime/turn-queue/); Hub/daemon transport (src/hub/: discovery/,
  daemon/, client/, server/handlers/); Connector supervision
  (src/services/connectors/, sdk/packages/shared/src/runtime/); Scheduling &
  teams (src/cron/specs/, src/session/team/); Agenda task kernel (src/tasks/);
  Hub schedule commands (src/cron/service/, src/hub/server/).
- Scope and retrieval questions: `references/index.md#use-this-for`.
- Complete capsule chooser: `references/index.md#load-the-matching-source-dump`.
- Detailed grouped map: `references/index.md#capsule-map`.
- Source limitations and portability boundaries: `references/index.md#boundaries`.

## Retrieval

Open the index, choose one capsule matching the active question, and load only
that capsule. Revalidate its cited source and revision before relying on it. Do
not bulk-load the inventory, treat historical claims as current truth, or apply
this foundation as a procedure.
