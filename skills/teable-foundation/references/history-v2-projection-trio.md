<!-- capsule-v2 -->
# V2 history projection trio & field meta extraction

## Source / Question
**Source:** teable `apps/nestjs-backend/src/features/v2/v2-record-history.service.ts` :265–361 (RecordUpdated), :368–471 (RecordsBatchCreated), :478–595 (RecordsBatchUpdated), :603–652 (registrar) — whole-file read pass 19.
**Question:** How does one history writer serve single-update, batch-create, and batch-update events without three divergent codepaths — and which skips differ per event?

## Path / Symbol
`V2RecordUpdatedHistoryProjection` / `V2RecordsBatchCreatedHistoryProjection` / `V2RecordsBatchUpdatedHistoryProjection`, all `@ProjectionHandler(<event>) implements IEventHandler<event>`; wired by `V2RecordHistoryService.registerProjections(container)` via `container.registerInstance(...)` ×3 under `@V2ProjectionRegistrar()`.

## Signature
```ts
handle(context: IExecutionContext, event: RecordUpdated|RecordsBatchCreated|RecordsBatchUpdated)
  : Promise<Result<void, DomainError>>   // always ok(undefined); real work deferred
```

## Data Shape
Shared entry shape IRecordHistoryEntry; shared meta extraction:
```ts
interface IFieldHistoryMeta { type: string; name: string;
  options: Record<string,unknown>|null|undefined; cellValueType: string; isComputed: boolean }
```

## Decisive source
```ts
// extractFieldMeta :197-213 — visitor-driven so v2 domain objects render in v1-compat shapes
const valueTypeResult = field.accept(new FieldValueTypeVisitor());
const cellValueType = valueTypeResult.isOk() ? valueTypeResult.value.cellValueType.toString() : 'string';
```
```ts
// per-event skip ladders (the ONLY differences between the three writers)
RecordUpdated:        kill-switch → source==='computed' → changes.length===0
RecordsBatchCreated:  kill-switch → union(fieldIds).size===0   // NO computed-source gate
RecordsBatchUpdated:  kill-switch → source==='computed' → union(fieldIds).size===0
// row loop skips (update pair): !meta → isEqual(old,new) → isComputed
// row loop skips (create pair): value==='' || null → !meta || meta.isComputed
```

## Flow / Invariant
1. **Field metadata map built ONCE per event** from a cross-record/cross-change field-id UNION (`new Set`), then `table.getField(f => f.id().equals(...))` per id — one table load serves every row.
2. **Meta resolution failures are silent per-cell drops**: invalid FieldId (`FieldId.create` err) or missing field on the table simply never enter the map; their changes are skipped at write time via `if (!meta) continue`. No error, no partial row.
3. **Create events write before=null**: `buildHistoryValue(null, meta)` — creation history rows are "appeared with value", not "changed from empty".
4. **Create skips empty-string and null VALUES** (`value === '' || value == null`) but update paths do NOT skip empty strings — clearing a cell IS an update worth recording (`oldValue='x', newValue=''`).
5. **The create projection has NO computed-source gate** because RecordsBatchCreated carries no source discriminator; import/paste-created rows always record. The two update projections drop `source==='computed'` events entirely — recalculation cascades must not masquerade as user edits.
6. **Registration order is explicit**: registrar resolves TableQueryService from the V2 container then registers three PRE-BUILT instances (deps passed through constructor) — projections are stateless singletons per container, resolved per-table via `v2ContainerService.getContainerForTable`.
7. **RECORD_HISTORY_CREATE re-emit fires for ALL THREE** with the touched recordIds — v1-side consumers see identical signals regardless of which engine wrote.

## Probe (direct tests)
Anchored at repo root (direct spec `features/v2/v2-record-history.service.spec.ts`, 313L):
- `describe('V2RecordUpdatedHistoryProjection')` asserts envelope + `created_by: 'usrHistWriter00000001'` (:90–161)
- batch-created spec pins `getContainerForTable('tblHistTable0000001')` routing + before.data=null (:205–232)
- batch-updated spec pins two records in ONE execute call (:293–311)

## Retrieve
```bash
codebase-memory-mcp cli search_code '{"project":"teable","pattern":"V2RecordsBatchCreatedHistoryProjection","limit":3}'
# → Class .../v2-record-history.service.ts 368-471 (+ registrar sites 632-640, spec Module)
```

## Verdict
**adopt** — the "one writer per event type over a shared meta extractor + per-event skip ladder" layout ports directly to any dual-engine (v1 ops / v2 domain-event) system that must keep audit parity between engines.
