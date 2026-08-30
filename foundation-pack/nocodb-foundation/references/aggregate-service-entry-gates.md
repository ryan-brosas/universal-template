<!-- capsule-v2 -->
# Source
NocoDB `develop@640fe3b06fb26c9d000e2258477001c0d5e62c73` — `packages/nocodb/src/services/data-table.service.ts` :125–141 + :1615–1641; `services/public-datas.service.ts` :337 + :1482.

# Question
What do the service-layer entry guards enforce before aggregation orchestration runs?

## Path / Symbol
`DataTableService.aggregate`, `DataTableService.bulkAggregate`; public twins in PublicDatasService.

## Signature
```ts
return await DBQueryClient.get(source.type).aggregate(context, { model, view, source, args: listArgs });
```

## Data Shape
listArgs = `{...param.query}` with `filterArr` and `aggregation` JSON-parsed from their `*Json` query params (try/catch — malformed JSON leaves the raw string in place for downstream parseFilterArrJson to 400); bulk body = array of buckets, JSON.parse-tolerated identically (:1623–1630).

## Decisive source
data-table.service.ts:125–128 / 1617–1619 — BOTH entries open with `NcError.badRequest('Aggregation is only supported on grid views')` when the resolved view isn't a grid — view-TYPE gate precedes any parsing. The PUBLIC twin (public-datas.service.ts `dataAggregate` :296–298) enforces the same gate with a different channel: `if (view.type !== ViewTypes.GRID) NcError.notFound('Not found')` — shared views hide existence rather than explain restrictions (consistent with shared-base-pseudo-user doctrine).
data-table.service.ts:140 — factory call uses `source.type` (the SOURCE's engine), not the model's or request's — a base's data lives where its source says.
bulk service :1632–1636 — bulkFilterList normalized from string-or-array BEFORE ctx construction; the orchestrator then validates per-bucket filters up-front (see bulk-aggregate-bucket-funnel).
UiPost.operations.ts:622 — the INTERNAL module surface calls the same service method, so internal automation inherits identical gates (no second code path).

## Flow / Invariant
Entry contract: grid-only → parse-tolerant → dialect client from SOURCE → one of two orchestrations. The gate order matters: a non-grid view with valid filters must 400 before touching user filter input, so error precedence is stable regardless of payload validity.

## Probe (direct test)
From repo root:
```
grep -rc 'Aggregation is only supported on grid views' packages/nocodb/src/services/data-table.service.ts   # => 2 (aggregate + bulkAggregate entries)
# public twin uses NcError.notFound('Not found') behind view.type !== ViewTypes.GRID (:296–298), NOT badRequest — semantic correction vs first draft
grep -c 'JSON.parse(listArgs.aggregation)' packages/nocodb/src/services/data-table.service.ts             # => 2 (:137 aggregate + :1627 bulk)
grep -c 'DBQueryClient.get(source.type)' packages/nocodb/src/services/data-table.service.ts               # => 2 (:140,:1634)
grep -n 'dataTableService.bulkAggregate' packages/nocodb/src/controllers/internal/modules/UiPost.operations.ts  # => 1 (:622)
```

## Retrieve
```
codebase-memory-mcp cli search_graph '{"project":"mnt-hdd-utopia-inspo-platforms-nocodb","query":"aggregate grid views badRequest","limit":3,"detail":"compact"}'
```
→ resolves both service aggregate/bulkAggregate methods.

## Verdict
**Adopt.** Port the three-part entry funnel (view-type gate → tolerant parse → source-typed dispatch) for any stats endpoint over user-defined views.
