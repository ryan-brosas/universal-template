<!-- capsule-v2 -->
# Source
NocoDB `develop@640fe3b06fb26c9d000e2258477001c0d5e62c73` — `packages/nocodb/src/dbQueryClient/cross-db-utils/aggregate.ts` :24–154 (orchestration) + :167–218 (`resolveAggregateColumns`).

# Question
How does a single-filter-set view-footer aggregation assemble its WHERE stack and resolve which columns aggregate?

## Path / Symbol
`aggregate(_client, logger?) → (context, ctx) => Promise<Record<string, unknown>>`; `resolveAggregateColumns({ baseModel, view, aggregation })`.

## Signature
Returns `{ [columnTitle]: value }` keyed by TITLE (mapped back from col.id aliases at :140–147).

## Decisive source
Filter-stack ORDER at :73–100 — exactly four ANDed groups, always in this sequence: (1) RLS conditions wrapped as one group; (2) view root filters ONLY when `baseModel.viewId` is set; (3) caller `args.filterArr`; (4) `where` string parsed via `extractFilterFromXwhere`. Then soft-delete filter appended SEPARATELY (:102–105 `qb.where(softDeleteFilter)` — outside the conditionV2 group array).
:109–120 — selectors built under `Promise.all` (parallel per-column applyAggregation), each pushed with alias = col.id; empty selector list after skips ⇒ `{}` returned WITHOUT querying (:122–124).
:128–134 — execAndParse flags `{first:true, bulkAggregate:true, skipDateConversion:true, skipAttachmentConversion:true, skipUserConversion:true}` — raw values on purpose: an aggregate row has no record identity for converters to key on.
resolveAggregateColumns (:182–206): view path iterates GridViewColumn.list keeping only `gc.show` columns, system fields dropped unless `view.show_system_fields`, then overrideMap narrows+overrides types when the caller passed explicit aggregation pairs; `isLinksOrLTAR(col) && col.system` excluded in BOTH paths (:201/:212). No-view path (:208–215): aggregation pairs are REQUIRED and are the sole source.
Error channel asymmetry: single aggregate rethrows after logging (:150–153).

## Flow / Invariant
Porter traps: (a) result keys are column TITLES not ids — the id→title map is applied post-query so callers see stable names even when ids change; (b) RLS enters FIRST so no later filter group can widen visibility; (c) soft-delete is a separate qb.where because it must survive conditionV2's group normalization.

## Probe (direct test)
From repo root:
```
sed -n '68,105p' packages/nocodb/src/dbQueryClient/cross-db-utils/aggregate.ts | grep -c "new Filter"   # => 4 groups
grep -n 'getSoftDeleteFilter' packages/nocodb/src/dbQueryClient/cross-db-utils/aggregate.ts             # => 1 (:102)
grep -c 'show_system_fields' packages/nocodb/src/dbQueryClient/cross-db-utils/aggregate.ts              # => 2 (:163 doc + :191 check)
sed -n '140,147p' packages/nocodb/src/dbQueryClient/cross-db-utils/aggregate.ts | grep -c 'idToTitle'   # => 2 (map build :140 + remap :146)
```

## Retrieve
```
codebase-memory-mcp cli search_graph '{"project":"mnt-hdd-utopia-inspo-platforms-nocodb","query":"aggregate orchestration rlsFilterGroup softDelete","limit":2,"detail":"compact"}'
```
→ `...cross-db-utils.aggregate.aggregate Function ... aggregate.ts 25-154`.

## Verdict
**Adopt.** The four-group filter ladder + title remap is the reusable contract for any "stats over a filtered view" endpoint.
