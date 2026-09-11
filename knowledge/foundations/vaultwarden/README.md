---
name: vaultwarden-foundation
description: "Use when porting E2E-encrypted vault server machinery — master-password verification kernels, issuer-partitioned JWT realms, refresh/stamp session invalidation, type-driven RBAC guards, trusted-proxy client IP, 2FA challenge protocols with anti-replay, Send one-time links, SSRF-guarded egress, layered config engines, and org key-escrow recovery."
kind: foundation
invocation: manual
disable-model-invocation: true
---
# vaultwarden: self-hosted Bitwarden-compatible vault server

## Foundation contract

This is a cold, source-specific foundation, not an operational procedure. It is
historical, revision-pinned evidence rather than timeless guidance. Current
project source, tests, requirements, and runtime behavior outrank this
projection and decide what ships.

## Provenance and revision

- Source record: `vaultwarden`; portable upstream identity, license, coverage caveats, and retrieval history are preserved in the index.
- Recorded revision: `main@46d71107f5094460dd5ecbe1dbac6e6c71e5189a`.
- Full provenance, coverage caveats, boundaries, and preserved evidence:
  `references/index.md`.

## Topic map

- Representative topics: Crypto kernel; Token realms; Sessions; Authorization;
  Network trust; Login flows; Second factors; Account lifecycle.
- Scope and retrieval questions: `references/index.md#use-this-for`.
- Complete capsule chooser: `references/index.md#load-the-matching-source-dump`.
- Detailed grouped map: `references/index.md#capsule-map`.
- Source limitations and portability boundaries: `references/index.md#boundaries`.

## Retrieval

Open the index, choose one capsule matching the active question, and load only
that capsule. Revalidate its cited source and revision before relying on it. Do
not bulk-load the inventory, treat historical claims as current truth, or apply
this foundation as a procedure.
