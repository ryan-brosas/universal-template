---
name: server-foundation
description: "Use when porting multi-engine push/notification fan-out, Azure Notification Hubs registration pools, tag-based targeting/exclusion grammars, installation-relay protocols for self-hosted instances, feature-flagged per-user vault-sync fan-out, or the real-time consumer side: SignalR hub group grammars and connect lifecycles, queue-consumer poll/poison loops, internal send ingress, wire-format contract tables across rolling deploys, and pre-auth token-as-group waiting rooms. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval."
kind: foundation
invocation: manual
disable-model-invocation: true
---
# Bitwarden server: push-notification platform foundation

## Foundation contract

This is a cold, source-specific foundation, not an operational procedure. It is
historical, revision-pinned evidence rather than timeless guidance. Current
project source, tests, requirements, and runtime behavior outrank this
projection and decide what ships.

## Provenance and revision

- Source record: `server`; portable upstream identity, license, coverage caveats, and retrieval history are preserved in the index.
- Recorded revision: `main@ac309aa19ed351406a56032d5f26a7a9a99f4abd`.
- Full provenance, coverage caveats, boundaries, and preserved evidence:
  `references/index.md`.

## Topic map

- Representative topics: Fan-out kernel; Hub pool; Tag grammar; Relay guards;
  Registration; Cipher sync; Hub groups; Queue consumer.
- Scope and retrieval questions: `references/index.md#use-this-for`.
- Complete capsule chooser: `references/index.md#load-the-matching-source-dump`.
- Detailed grouped map: `references/index.md#capsule-map`.
- Source limitations and portability boundaries: `references/index.md#boundaries`.

## Retrieval

Open the index, choose one capsule matching the active question, and load only
that capsule. Revalidate its cited source and revision before relying on it. Do
not bulk-load the inventory, treat historical claims as current truth, or apply
this foundation as a procedure.
