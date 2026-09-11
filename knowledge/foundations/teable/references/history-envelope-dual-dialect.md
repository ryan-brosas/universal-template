<!-- capsule-v2 -->
# History envelope dual dialect (meta vs bare)

## Source / Question
**Source:** teable `apps/nestjs-backend/src/features/record/record.service.ts` `createRecordsOnlySql` (:1397–1502, whole-range read pass 19) vs `event-emitter/listeners/record-history.listener.ts` :104–121 and `features/v2/v2-record-history.service.ts` `buildHistoryValue` :248–259.
**Question:** What EXACTLY must a history row's before/after JSON look like — and why do two of the three writers emit a different shape?

## Path / Symbol
- v1 listener + v2 projections: `{ meta: { type, name, options, cellValueType }, data }`
- SQL fast path (`createRecordsOnlySql`, used by API bulk create): `JSON.stringify({ data: null })` / `JSON.stringify({ data: value })`

## Signature
```ts
// full envelope (listener + v2)
{ meta: { type: string; name: string; options: Record<string,unknown>|null|undefined;
          cellValueType: string /* +isComputed in v2 meta */ }, data: unknown }
// bare envelope (SQL fast path)
{ data: unknown }   // NO meta key at all
```

## Data Shape
Same physical table `record_history(id 'rhi…', table_id, record_id, field_id, before TEXT, after TEXT, created_by)`; the JSON payload inside before/after has TWO dialects.

## Decisive source
```ts
// record.service.ts :1463-1464 (SQL fast path — deliberately bare)
before: JSON.stringify({ data: null }),
after:  JSON.stringify({ data: value }),
```
```ts
// v2-record-history.service.ts :248-259 (full envelope)
const buildHistoryValue = (value, meta) => ({
  meta: { type: meta.type, name: meta.name,
          options: minimizeFieldOptions(value, meta), cellValueType: meta.cellValueType },
  data: value,
});
```

## Flow / Invariant
1. **The read plane is the compat contract**: `record-history-cold-read.service.ts` merged reads and the UI render guard treat missing meta as "render data only" — cold-storage pass 18 pinned `coldTruncated===true` render guards against THIS table, so any new writer must either write full envelopes or verify readers tolerate bare ones.
2. **Why bare on the fast path**: `createRecordsOnlySql` builds one multi-row INSERT for records AND a second for history in the same request; per-cell field metadata was already resolved as field INSTANCES for column mapping — emitting full envelopes would double JSON serialization cost on import-sized batches.
3. **v1 listener and all three v2 projections always write FULL envelopes** (spec-pinned byte-shape: `expect(JSON.parse(rows[0].before)).toEqual({ meta: {...}, data: 'before' })`).
4. **Select-choice minimization is part of the envelope, not post-processing**: options.choices are filtered to choices matching the VALUE at write time (string equality / Set membership for arrays; null → `choices: []`). A porter that stores the whole choices list bloats every row and changes diff rendering.

## Probe (direct tests)
Anchored at repo root:
```bash
grep -cF 'JSON.stringify({ data: null })' apps/nestjs-backend/src/features/record/record.service.ts   # → 1
grep -cF 'JSON.stringify({ data: value })' apps/nestjs-backend/src/features/record/record.service.ts  # → 1
grep -c 'meta:' apps/nestjs-backend/src/features/v2/v2-record-history.service.ts                      # → 4
```

## Retrieve
```bash
codebase-memory-mcp cli search_code '{"project":"teable","pattern":"buildHistoryValue","limit":3}'
# → Function .../features/v2/v2-record-history.service.ts 248-259 (+ both call sites 346-347 / 452-453)
```

## Verdict
**adapt** — pick ONE dialect per writer; if porting the reader too, mirror teable's rule: full envelope when metadata context matters (UI diffs), bare when write throughput dominates (bulk import). Never mix within one write path.
