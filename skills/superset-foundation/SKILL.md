---
name: superset-foundation
description: "Use when porting Apache Superset's chart-data acquisition kernel (per-query cache-key composition under security context, cache fault-tolerance ladders, contribution-totals two-phase sync, annotation-data co-caching, cache-timeout precedence, grouping-sets emulation), its chart-data HTTP entry plane (sync/async job gate with identity-carrying submission, opaque-key cache replay with novel-SQL skip, annotation-layer permission gating, override-before-reauthorization, authorize-before-render ordering), or its Alerts & Reports execution plane (crontab-keyed state machine, WORKING concurrency guard, audit-log row promotion, retry/backoff ladder with window anchors, error-notification grace dedup, webhook SSRF peer validation and response containment). Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval."
kind: foundation
invocation: manual
disable-model-invocation: true
---
# Superset: chart-data execution & alerts/reports scheduling foundation

## Foundation contract

This is a cold, source-specific foundation, not an operational procedure. It is
historical, revision-pinned evidence rather than timeless guidance. Current
project source, tests, requirements, and runtime behavior outrank this
projection and decide what ships.

## Provenance and revision

- Source record: `superset`; portable upstream identity, license, coverage caveats, and retrieval history are preserved in the index.
- Recorded revision: `master@9f505eb0cbbc39b78f512765d82fd63cf5ad70e6`.
- Full provenance, coverage caveats, boundaries, and preserved evidence:
  `references/index.md`.

## Topic map

- Representative topics: Payload acquisition; Cache compatibility; Cache fault
  tolerance; Annotation security binding; Contribution totals; Key stability;
  Timeout precedence; Rollup emulation.
- Scope and retrieval questions: `references/index.md#use-this-for`.
- Complete capsule chooser: `references/index.md#load-the-matching-source-dump`.
- Detailed grouped map: `references/index.md#capsule-map`.
- Source limitations and portability boundaries: `references/index.md#boundaries`.

## Retrieval

Open the index, choose one capsule matching the active question, and load only
that capsule. Revalidate its cited source and revision before relying on it. Do
not bulk-load the inventory, treat historical claims as current truth, or apply
this foundation as a procedure.
