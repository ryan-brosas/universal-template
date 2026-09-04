---
name: chatwoot-foundation
description: "Use when porting Chatwoot-style multi-tenant SaaS mechanics — account-scoped event fanout to per-account webhook subscriptions, HMAC-signed outbound webhook delivery with retry classification, Redis round-robin agent assignment with row-lock race discipline, API-token tenant resolution with bot endpoint allowlists, bit-packed feature flags, and editor-markdown webhook payload hygiene."
kind: foundation
invocation: manual
disable-model-invocation: true
---
# Chatwoot: Multi-Tenant Event Fanout, Webhook Dispatch, and Auto-Assignment Foundation

## Foundation contract

This is a cold, source-specific foundation, not an operational procedure. It is
historical, revision-pinned evidence rather than timeless guidance. Current
project source, tests, requirements, and runtime behavior outrank this
projection and decide what ships.

## Provenance and revision

- Source record: `chatwoot`; portable upstream identity, license, coverage caveats, and retrieval history are preserved in the index.
- Recorded revision: `develop@6154aebcfea1fe62e8dd01fbf94568ef827fc51c`.
- Full provenance, coverage caveats, boundaries, and preserved evidence:
  `references/index.md`.

## Topic map

- Representative topics: Event dispatch fanout; Webhook subscription model;
  HMAC webhook delivery; Agent-bot retry ladder; Webhook error compensation;
  SafeFetch SSRF boundary; Round-robin Redis queue; Legacy V1 in-save
  assignment.
- Scope and retrieval questions: `references/index.md#use-this-for`.
- Complete capsule chooser: `references/index.md#load-the-matching-source-dump`.
- Detailed grouped map: `references/index.md#capsule-map`.
- Source limitations and portability boundaries: `references/index.md#boundaries`.

## Retrieval

Open the index, choose one capsule matching the active question, and load only
that capsule. Revalidate its cited source and revision before relying on it. Do
not bulk-load the inventory, treat historical claims as current truth, or apply
this foundation as a procedure.
