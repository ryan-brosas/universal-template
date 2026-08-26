<!-- capsule-v2 -->
# Ops→history event pipeline (v1 emission side)

## Source / Question
**Source:** teable `apps/nestjs-backend/src/event-emitter/event-emitter.service.ts` (421L, whole read pass 19) + `share-db/share-db.service.ts` :80–93.
**Question:** How do raw ShareDB ops become the aggregated RecordUpdateEvent that the history listener consumes — and where do oldField and isBulk come from?

## Path / Symbol
`EventEmitterService.ops2Event(rawOpMaps)` (:85–110) → `collectEventsFromRawOpMap` → `generateEventsFromRawOps` → `createEvent` → RxJS `groupBy(tableId_eventName)` → `aggregateEventsByGroup(toArray→combineEvents)` → `emitAsync`.

## Signature
```ts
async ops2Event(rawOpMaps?: IRawOpMap[]): Promise<void>
// collection key grammar: `${docType}_${docId}` split into [docType, docId]
```

## Data Shape
Per-record merged change object: `{ [fieldId]: { oldValue, newValue } }`; bulk events carry arrays under payload.record with `isBulk: true`.

## Decisive source
```ts
// createEvent :304-308 — CLS-injected conversion context, ONLY for record updates
const oldField = this.cls.get('oldField');
if (eventName === Events.TABLE_RECORD_UPDATE) { payload.oldField = oldField; }

// mergeEventsForUpdate :248-257 — a CREATE followed by an EDIT on the same record id
// collapses into ONE TABLE_RECORD_UPDATE whose fields are newValue-only maps
if ([RawOpType.Create, RawOpType.Edit].includes(rawOpType) &&
    event.name === Events.TABLE_RECORD_UPDATE) {
  const fields = this.getUpdateFieldsFromEvent(event, rawOpType); // Edit: as-is; Create: value.newValue per field
  event = this.combineUpdateEvents(existingEvent, fields);
}
```

## Flow / Invariant
1. **Emission is post-commit by construction**: share-db.service binds ops2Event in `bindAfterTransaction`, reading AND clearing `cls tx.rawOpMaps` first (`this.cls.set('tx.rawOpMaps', undefined)` :82) — events can never fire for a rolled-back write, and never double-fire for retried commits.
2. **Grouping key is `${tableId}_${eventName}`** so bulk edits over one table aggregate into ONE event with record ARRAY payloads; the history listener's Array.isArray branch exists because of this aggregator, not because single ops produce arrays.
3. **Mixed-shape change cells are real**: after create+edit merging a field entry may be `{newValue}` only (no oldValue) — which is exactly why the listener's filter step 2 tests `'oldValue' in changeValue && 'newValue' in changeValue` instead of truthiness.
4. **oldField rides CLS, not the op**: field-conversion flows stash the pre-conversion Field into `cls('oldField')`; the emitter copies it onto every record-update event created during that request. A porter must preserve "context captured at request time" semantics or lose before-side metadata during type conversions.
5. **User identity also comes from CLS** (`createExtendPlainContext` :211–225 reads `cls user/entry`) — v1 attribution is request-scoped, unlike v2's snapshot actorId.

## Probe (direct tests)
Anchored at repo root:
```bash
grep -cF 'payload.oldField = oldField' apps/nestjs-backend/src/event-emitter/event-emitter.service.ts  # → 1
grep -c 'RawOpType.Create, RawOpType.Edit' apps/nestjs-backend/src/event-emitter/event-emitter.service.ts  # → 1
grep -cF 'isBulk: true' apps/nestjs-backend/src/event-emitter/event-emitter.service.ts  # → 1
grep -c bindAfterTransaction apps/nestjs-backend/src/share-db/share-db.service.ts       # → 1
```

## Retrieve
```bash
codebase-memory-mcp cli search_code '{"project":"teable","pattern":"combineUpdateEvents","limit":3}'
# → Method .../event-emitter/event-emitter.service.ts (private; resolves via call-site hits)
```

## Verdict
**adopt** — the ops→events aggregation contract (post-commit emission, table-scoped bulk merge, CLS-riding conversion metadata) is the reusable seam for any OT/ShareDB-backed audit pipeline.
