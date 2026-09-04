<!-- capsule-v2 -->
# Record-history buffer capture funnel (v1 listener)

## Source / Question
**Source:** teable `apps/nestjs-backend/src/event-emitter/listeners/record-history.listener.ts` (174L, whole-file read pass 19).
**Question:** How does a table.record.update op become per-cell history rows WITHOUT touching the request's transaction or latency?

## Path / Symbol
`RecordHistoryListener.recordUpdateListener` — `@OnEvent(Events.TABLE_RECORD_UPDATE, { async: true })` (:27). Event name `'table.record.update'` defined in `event-emitter/events/event.enum.ts` :28.

## Signature
```ts
async recordUpdateListener(event: RecordUpdateEvent): Promise<void>
// event.payload: { tableId, record: IChangeRecord | IChangeRecord[], oldField?: Field }
// event.context.user?: { id }   (CLS user captured by EventEmitterService.createExtendPlainContext)
```

## Data Shape
Row inserted into `record_history` (snake_case columns):
`{ id: 'rhi'+24rand, table_id, record_id, field_id, before: JSON string, after: JSON string, created_by: userId }`.
`before`/`after` envelope: `{ meta: { type, name, options, cellValueType }, data: <cellValue> }`.

## Decisive source
```ts
if (this.baseConfig.recordHistoryDisabled) return;            // kill switch FIRST
...
const fields = await this.dataLoaderService.field.load(tableId, { id: fieldIds }); // ONE batched load
...
if (!field || !changeValue || !isObject(changeValue)) return null;        // 1 malformed cell
if (!('oldValue' in changeValue) || !('newValue' in changeValue)) return null; // 2 wrong shape
const oldField = _oldField ?? field;                            // 3 field-type-change latch
if (isEqual(oldValue, newValue)) return null;                   // 4 no-op skip
if (oldField.isComputed && isComputed) return null;             // 5 both-computed skip
```
(:29–97, condensed)

## Flow / Invariant
Emission chain: ShareDB commit → `share-db.service.ts` `bindAfterTransaction` (:80–93) reads+clears `cls tx.rawOpMaps` THEN calls `eventEmitterService.ops2Event(ops)` → ops grouped by `${tableId}_${eventName}`, bulk-aggregated (`isBulk: true`) and emitted async → this listener runs OUTSIDE any request transaction.
Invariants a porter gets wrong:
1. **Kill switch is env-level**: `RECORD_HISTORY_DISABLED === 'true'` (base.config.ts :14) — checked once at config load, gates only HISTORY WRITES, never reads.
2. **Cross-record field-id UNION**: field ids collected from ALL records into one Set BEFORE one dataloader fetch — N records cost 1 field query.
3. **The five-step filter ladder ORDER matters**: shape checks precede equality; equality precedes computed-skip. A porter that drops step 2 crashes on create-shaped cells (`{newValue}` only, merged from RecordCreate events by EventEmitterService.combineUpdateEvents :279–296).
4. **`_oldField ?? field` latch**: during a field-type conversion the CLS `oldField` (set by field-conversion flows) supplies the BEFORE-side metadata; using the current field for both sides would falsify `meta.type` of the before snapshot.
5. **Both-computed skip is asymmetric on purpose**: computed→computed transitions (recalculation cascades) produce no history; user edits OF a formerly-computed field DO.
6. **Batch insert is schema-qualified through the router**: `dataKnex.withSchema(new URL(dataDbUrl).searchParams.get('schema') || 'public')` then `.insert(list).into('record_history').toQuery()` executed via `databaseRouter.executeDataPrismaForTable(tableId, query)` — raw SQL because the data DB is routed per-table (BYODB) and Prisma's models live on the main client.
7. **5000-row slices**: inserts chunked `for (i += batchSize)` so one giant bulk edit cannot build an unbounded statement.
8. **Re-emit is unconditional**: `emit(RECORD_HISTORY_CREATE, { recordIds })` fires even when zero rows were written (:141–143) — it signals "update processed", not "rows exist".

## Probe (direct tests)
Anchored at repo root `$REFERENCE_ROOT/platforms/teable`:
```bash
grep -c recordHistoryDisabled apps/nestjs-backend/src/event-emitter/listeners/record-history.listener.ts  # → 1
grep -cF 'isEqual(oldValue, newValue)' apps/nestjs-backend/src/event-emitter/listeners/record-history.listener.ts  # → 1
grep -cF '_oldField ?? field' apps/nestjs-backend/src/event-emitter/listeners/record-history.listener.ts  # → 1
grep -c "into('record_history')" apps/nestjs-backend/src/event-emitter/listeners/record-history.listener.ts  # → 1
```
No dedicated unit spec exists for the v1 listener (coverage caveat: behavior pinned indirectly by `v2-record-history.service.spec.ts` asserting the SAME envelope contract for v2).

## Retrieve
```bash
codebase-memory-mcp cli search_code '{"project":"teable","pattern":"RecordHistoryListener","limit":3}'
# → Class apps/nestjs-backend/src/event-emitter/listeners/record-history.listener.ts 19-174
```

## Verdict
**adopt** — the funnel (batched field load → filter ladder → schema-qualified raw insert → re-emit) ports as-is to any ShareDB/op-log-backed app needing per-cell audit rows off the hot path.
