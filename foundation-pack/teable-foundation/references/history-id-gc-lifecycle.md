<!-- capsule-v2 -->
# History id grammar, kill switch & lifecycle GC

## Source / Question
**Source:** teable `packages/core/src/utils/id-generator.ts` :210–212 + IdPrefix :43; `apps/nestjs-backend/src/configs/base.config.ts` :14; `features/table/open-api/table-open-api.service.ts` `dropTables` (:612–631) + `cleanupColdHistoryPrefixes` (:475–487); `features/record-history-cold/` (pass-18 plane).
**Question:** What surrounds the buffer — how are rows identified, how is capture switched off, and when do rows die?

## Path / Symbol
- `generateRecordHistoryId(): 'rhi' + getRandomString(24)` (`IdPrefix.RecordHistory = 'rhi'`)
- Kill switch: `recordHistoryDisabled: process.env.RECORD_HISTORY_DISABLED === 'true'`
- Buffer GC: `dataPrisma.recordHistory.deleteMany({ where: { tableId: { in: tableIds } } })`

## Data Shape
Kill-switch semantics: evaluated ONCE at config load (not per request). GC semantics: best-effort, AFTER purge commit, cold prefix deletion decoupled.

## Decisive source
```ts
// table-open-api.service.ts :618-621 — buffer rows die with the table, best-effort
await bestEffort(`record history for tables ${tables}`, () =>
  dataPrisma.recordHistory.deleteMany({ where }));
// ...and ONLY THEN (:475-487), outside the tx:
await this.recordHistoryColdStorage.deleteTablePrefix(tableId)
  .catch((error) => this.logger.warn(`failed to delete cold history prefix for ${tableId}: ${error}`));
```
(dropTables comment: "The delete is irreversible, so it must only run AFTER the DB purge transaction has committed — never inside it (a rollback would restore the table without its cold history). An S3 miss never fails the purge.")

## Flow / Invariant
1. **One env var gates all three writers** (v1 listener + two v2 update projections + v2 create projection all read `baseConfig.recordHistoryDisabled`) — but gates WRITES only; reads (merged history API) stay live so shared-DB deployments keep visibility. Mirrors pass-18's cold-storage kill-switch ruling: flush/compact/delete gated, merged reads unconditional.
2. **`rhi`+24 grammar is collision-space, not secrecy** — ids generated client-side in every writer via the same core util; no DB sequence. Porters must keep the prefix stable: cold-storage part keys and stats embed record-id ranges keyed off this id space.
3. **Table deletion drains BOTH tiers in a fixed order**: hot buffer rows first (best-effort inside the data-db step), then irreversible S3 prefix removal strictly after the purge transaction commits — reversing the order risks restoring a table whose cold history is already gone.
4. **GC failures never fail table deletion**: every surrounding call is `bestEffort(...)` / `.catch(warn)`; ops tooling reconciles leftovers against table existence.
5. **No per-record or per-field GC exists at this layer**: buffer rows accumulate until table drop or pass-18's retention flusher moves them to cold parts; there is deliberately NO TTL delete job on `record_history`.

## Probe (direct tests)
Anchored at repo root:
```bash
grep -c "RecordHistory = 'rhi'" packages/core/src/utils/id-generator.ts                                # → 1
grep -cF "process.env.RECORD_HISTORY_DISABLED === 'true'" apps/nestjs-backend/src/configs/base.config.ts  # → 1
grep -c recordHistory.deleteMany apps/nestjs-backend/src/features/table/open-api/table-open-api.service.ts # → 1
grep -cF "bestEffort(\`record history" apps/nestjs-backend/src/features/table/open-api/table-open-api.service.ts # → 1
```

## Retrieve
```bash
codebase-memory-mcp cli search_code '{"project":"teable","pattern":"generateRecordHistoryId","limit":3}'
# → Function packages/core/src/utils/id-generator.ts 210-212 (+ import sites incl. both writers)
```

## Verdict
**adopt** — id grammar + single write-side kill switch + tiered post-commit GC ordering form the lifecycle contract that makes the append-only buffer safe to port.
