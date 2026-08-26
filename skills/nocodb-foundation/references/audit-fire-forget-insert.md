<!-- capsule-v2 -->
# Audit fire-and-forget insert — how does mandatory audit logging never block or fail the operation it observes?

**Source:** nocodb (Sustainable Use License) `develop@640fe3b06fb2`; Codebase Memory `nocodb`. **Question:** Audit rows must be written for every mutation but must never break one — what is the await/error/kill-switch discipline?

## Unawaited-by-default insert with TEST-only determinism and a global kill switch
**Path/Symbol:** `packages/nocodb/src/models/Audit.ts:Audit.insert` (:44–121); keyset reader `recordAuditList` (:123–175).
**Signature:** `static insert(audit: Partial<Audit> | Partial<Audit>[], ncAudit = Noco.ncAudit, { forceAwait, catchException = false } = { forceAwait: process.env['TEST'] === 'true' })`.
**Data Shape:** row props allow-list (~19 id/op fields); `details` JSON column via stringifyMetaProp(a,'details'); static limit=25.

### Decisive source
```ts
// Will only await for Audit insertion if forceAwait is true, true in test environment by default
if (process.env.NC_DISABLE_AUDIT === 'true') return;
const insertAudit = async () => { /* extractProps allow-list + details:stringifyMetaProp;
                                     bulk path filters falsies then bulkMetaInsert */ };
if (forceAwait) {
  return await insertAudit();
} else {
  insertAudit().catch((e) => { console.error('Error inserting audit', e); });
  return;
}
```
(:43–113, condensed)

**Flow:** kill-switch check → shape branch (array ⇒ filter falsies + per-row details stringify + bulkMetaInsert; single ⇒ extractProps + metaInsert2) → fire-and-forget with attached .catch(console.error) unless forceAwait.
**Invariant:** the OBSERVED operation never waits on audit latency and never fails because of it — the only awaited mode is tests (`TEST==='true'`) where determinism beats realism; errors are logged, never propagated, unless catchException flips rethrow for callers that want audit failures loud; NC_DISABLE_AUDIT short-circuits BEFORE any shaping. The read twin `recordAuditList` pins its own contract: cursor format is `id|created_at` but ONLY the id segment keys the WHERE (`id < cursor-id`, keyset not OFFSET), the workspace where-clause is conditional, and pagination truth comes from fetching limit+1 then popping the overflow (`isLastPage:false` iff the extra row existed — 3 probe-visible occurrences). `baseAuditList` (:177–236) is deprecated TODO-only with unit-test consumers: do NOT port it as the list pattern. Cross-ref: keyset-backfill-walk (write-side walk of the same family).
**Probe:** `grep -c "NC_DISABLE_AUDIT" packages/nocodb/src/models/Audit.ts` (=1) · `grep -c "forceAwait" packages/nocodb/src/models/Audit.ts` (=5: doc comment, destructure, type, default-object, if) · `grep -c "this.limit + 1" packages/nocodb/src/models/Audit.ts` (=1 lookahead) · `grep -c "isLastPage" packages/nocodb/src/models/Audit.ts` (=3: empty-guard true + false + final true) · `grep -c "cursor?.split" packages/nocodb/src/models/Audit.ts` (=1).
**Direct test:** none upstream beyond shells for this plane — probes pin shape.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "Audit insert recordAuditList bulkMetaInsert forceAwait", limit: 10 });
```

## Verdict
Adopt unawaited audit with .catch-logging plus env kill-switch and a test-only await flag whenever observability must not tax the hot path; adapt the allow-list of persisted columns and the cursor wire format; omit the deprecated baseAuditList page-number path entirely. Coverage caveat: grep-pinned only; full-file direct read performed (237 lines).
