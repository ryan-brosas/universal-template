---
name: node-best-practices-foundation
description: "Use when porting Node.js production practice contracts: error-handling and crash predicates, project structure, testing patterns, Docker/ops choreography, and the security plane (headers, sessions, password KDFs, JWT revocation, injection/ReDoS guards, brute-force limiters, secret hygiene, sandbox ladders, OWASP checklist)."
kind: foundation
invocation: manual
disable-model-invocation: true
---
# Node.js Best Practices Foundation

## Foundation contract

This is a cold, source-specific foundation, not an operational procedure. It is
historical, revision-pinned evidence rather than timeless guidance. Current
project source, tests, requirements, and runtime behavior outrank this
projection and decide what ships.

## Provenance and revision

- Source record: `node-best-practices`; portable upstream identity, license, coverage caveats, and retrieval history are preserved in the index.
- Recorded revision: `master@dc3d60c29d5483d9ea99cf261bbd6203516a2ba7`.
- Full provenance, coverage caveats, boundaries, and preserved evidence:
  `references/index.md`.

## Topic map

- Representative topics: Error handling; Structure & testing; Runtime & ops;
  Web surface security; Crypto & identity; Injection & execution safety;
  Traffic & dependency hardening; Hygiene & governance.
- Scope and retrieval questions: `references/index.md#use-this-for`.
- Complete capsule chooser: `references/index.md#load-the-matching-source-dump`.
- Detailed grouped map: `references/index.md#capsule-map`.
- Source limitations and portability boundaries: `references/index.md#boundaries`.

## Retrieval

Open the index, choose one capsule matching the active question, and load only
that capsule. Revalidate its cited source and revision before relying on it. Do
not bulk-load the inventory, treat historical claims as current truth, or apply
this foundation as a procedure.
