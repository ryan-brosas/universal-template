<!-- capsule-v2 -->
# Event-snapshot clone discipline — "Why must every consumer of a pre-write event snapshot receive a deep copy?"

**Source:** twenty-crm AGPL-3.0 `main@9e4717278c29efa3ba0c147f6acf0d68e99a625c`; Codebase Memory `ext-twenty-crm`. **Question:** What breaks if formatting/validation helpers mutate the shared pre-write record objects used for before/after event diffs?

## structuredClone at the snapshot boundary
**Path/Symbol:** `packages/twenty-server/src/engine/twenty-orm/repository/workspace-update-query-builder.ts` (8 sites :169, :201, :256, :276, :359, :366, :455, :488).
**Signature:** `structuredClone(await eventSelectQueryBuilder.getMany({ noFormatting: true }))` — plus clones feeding formatResult and mergeRecordWithUpdateValues.
**Data Shape:** Unformatted DB rows whose nested composite values are plain objects; legacy formatters reconstruct embedded composites from flattened physical columns IN PLACE.

### Decisive source (commit 98ed14d9 "Fix legacy composite update event snapshots")
```ts
const before = structuredClone(
  await eventSelectQueryBuilder.getMany({ noFormatting: true }),
);
// ... every downstream consumer re-clones:
formatResult<T[]>(structuredClone(before), ...)
mergeRecordsWithUpdateValues(structuredClone(before), valuesSet)
structuredClone(getUpdateEventRecords(before, after))
```

**Flow:** Snapshot read once → cloned per consumer: RLS validation gets its own copy, formattedBefore another, updatedRecords reconstruction another → no helper can rewrite a nested composite inside recordsBefore → before/after diff stays truthful even though the legacy formatter mutates what it receives. Live QA on v2.34 proved composite-only updates persisted with NO internal event/timeline row when copies were shallow; scalar control updates worked, which is why tests that enabled ORM v2 missed it (production default is the mutating legacy ORM).
**Invariant:** Treat the pre-write snapshot as immutable-by-discipline: each formatting/validation/reconstruction path gets an isolated deep working copy. A shallow copy is NOT enough — the mutation happens on NESTED composite objects one level down.
**Probe:** `grep -c 'structuredClone' packages/twenty-server/src/engine/twenty-orm/repository/workspace-update-query-builder.ts` → 8; regression suite `src/modules/timeline/__tests__/timeline-activity.integration.spec.ts` runs the composite contract against BOTH ORMs with separate records (per 98ed14d9).

## Get live surrounding code
**Retrieve:**
```bash
codebase-memory-mcp cli search_graph '{"project":"ext-twenty-crm","query":"structuredClone before snapshot update builder","limit":5,"detail":"ids"}'
```

## Verdict
Adopt clone-at-boundary for any cached/shared pre-write state fed into mutating normalizers. Adapt: hosts with pure formatters may drop some clones, but keep them while any formatter mutates inputs. Omit nothing — this is the bug class itself. Caveat: behavioral proof lives in upstream integration specs requiring a full server test env; the count probe is the deterministic pin here.
