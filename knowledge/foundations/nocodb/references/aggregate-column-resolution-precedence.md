<!-- capsule-v2 -->
# Source
NocoDB `develop@640fe3b06fb26c9d000e2258477001c0d5e62c73` — `packages/nocodb/src/dbQueryClient/cross-db-utils/aggregate.ts` :167–218 (`resolveAggregateColumns`) + `types.ts` :24–44 (AggregateCtx/BulkAggregateCtx docs).

# Question
How do two heterogeneous "which columns aggregate" inputs — view-column config vs explicit pairs — normalize into one typed list?

## Path / Symbol
`resolveAggregateColumns({ baseModel, view, aggregation }) → Promise<AggregateColumnSpec[]>`; `AggregateCtx.args.aggregation` doc: "REQUIRED when no view is passed".

## Signature
```ts
interface AggregateColumnSpec { col: Column; aggregation: string }
```

## Data Shape
Input A: viewId set → GridViewColumn.list rows carry per-column `gc.aggregation` + `gc.show`.
Input B: `args.aggregation = [{field, type}]` where field is a COLUMN ID; Map-keyed override.

## Decisive source
aggregate.ts:177–180 — overrideMap built once; **`overrideMode = !!aggregation?.length`** — an EMPTY array is NOT override mode (falls back to view config), a non-empty one narrows+overrides.
:182–205 — view path: `columnsById[gc.fk_column_id]` missing ⇒ skip (deleted column still in view config); `!gc.show` skip; system fields skipped unless `view?.show_system_fields`; overrideMode ⇒ keep ONLY mapped columns and take type from the map; else `aggType = gc.aggregation`; empty aggType ⇒ skip; finally `isLinksOrLTAR(col) && col.system` excluded (:201).
:208–215 — no-view path: explicit pairs are the SOLE source (`if (overrideMode)`), resolved via columnsById with the same system-links exclusion; unknown field ids silently skipped.
types.ts:32–33 pins the requirement in prose on the interface itself so callers see it at type-time.

## Flow / Invariant
The precedence ladder porters must preserve: explicit-pairs > view-config > nothing. And within the view path, visibility (`show`) gates BEFORE aggregation-type resolution — hiding a column removes its aggregate even if an explicit pair names it... EXCEPT the pair path bypasses `gc.show` entirely when no view exists. Two callers (single + bulk orchestrations) share this function so their semantics cannot drift.

## Probe (direct test)
From repo root:
```
grep -c 'overrideMode' packages/nocodb/src/dbQueryClient/cross-db-utils/aggregate.ts   # => 3 sites (:180,:194,:208)
sed -n '188,205p' packages/nocodb/src/dbQueryClient/cross-db-utils/aggregate.ts | grep -c 'continue'   # => 6 skips (:189 col-missing, :190 hidden, :191 system-fields-off, :195 not-in-override-map, :200 no-agg-type, :201 system-links)
grep -c 'isLinksOrLTAR' packages/nocodb/src/dbQueryClient/cross-db-utils/aggregate.ts  # => 3 (:3 import + :201 + :212)
```

## Retrieve
```
codebase-memory-mcp cli search_graph '{"project":"mnt-hdd-utopia-inspo-platforms-nocodb","query":"resolveAggregateColumns","limit":2,"detail":"compact"}'
```
→ `...cross-db-utils.aggregate.resolveAggregateColumns Function ... aggregate.ts 167-218`.

## Verdict
**Adopt.** One normalizer for both shapes is what keeps single and bulk aggregation consistent — port it as the shared entry both paths call.
