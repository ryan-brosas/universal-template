---
name: ghost-foundation
description: "Use when porting Ghost's outbound webhook dispatch engine (HMAC signing, 410 tombstones, SSRF client selection, plan-limit suppression), scheduled-publishing machinery (JWT-signed schedule URLs, in-memory wake ladder, tolerance-based publish decisions), admin session/API-key auth planes (origin-pinned CSRF, email MFA challenges, kid-addressed JWT verification), or the lazy URL service (per-call URL resolution/generation with derived required-shape inference, NQL filter compatibility stripping, thin-resource degrade reporting, canonical reverse lookup, boot readiness gating). Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval."
kind: foundation
invocation: manual
disable-model-invocation: true
---
# Ghost: publishing-platform foundation

## Foundation contract

This is a cold, source-specific foundation, not an operational procedure. It is
historical, revision-pinned evidence rather than timeless guidance. Current
project source, tests, requirements, and runtime behavior outrank this
projection and decide what ships.

## Provenance and revision

- Source record: `ghost`; portable upstream identity, license, coverage caveats, and retrieval history are preserved in the index.
- Recorded revision: `81292b004cf59591f03d7dbe01f28f31c09ee813`.
- Full provenance, coverage caveats, boundaries, and preserved evidence:
  `references/index.md`.

## Topic map

- Representative topics: Webhook dispatch; SSRF client choice; Delivery
  lifecycle; Plan limits; Event wiring; Payload shape; Pipeline assembly;
  Inbound validation.
- Scope and retrieval questions: `references/index.md#use-this-for`.
- Complete capsule chooser: `references/index.md#load-the-matching-source-dump`.
- Detailed grouped map: `references/index.md#capsule-map`.
- Source limitations and portability boundaries: `references/index.md#boundaries`.

## Retrieval

Open the index, choose one capsule matching the active question, and load only
that capsule. Revalidate its cited source and revision before relying on it. Do
not bulk-load the inventory, treat historical claims as current truth, or apply
this foundation as a procedure.
