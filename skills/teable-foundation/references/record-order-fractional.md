<!-- capsule-v2 -->
# Fractional record ordering — how do you insert K records between two others without rewriting the table?

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** How are per-view record positions calculated so inserts between neighbors stay cheap, yet never collide even after unbounded inserts?

## Midpoint keys with full-shuffle escape hatch
**Path/Symbol:** `packages/v2/adapter-table-repository-postgres/src/record/repository/PostgresRecordOrderCalculator.ts:PostgresRecordOrderCalculator.calculateOrders` (31–121); lazy column `ensureOrderColumnExists` (140–166); rebalance `shuffleRecords` (168–182); port `packages/v2/core/src/ports/RecordOrderCalculator.ts:IRecordOrderCalculator`; noop default `ports/defaults/NoopRecordOrderCalculator.ts`.
**Signature:** `calculateOrders(context, table, viewId, anchorId: RecordId, position: 'before'|'after', count: number): Promise<Result<ReadonlyArray<number>, DomainError>>`.
**Data Shape:** order values are `double precision` in a PER-VIEW column `__row_<viewId>` added lazily to the table's dynamic physical table; seeded once from `__auto_number`; btree-indexed with a hash-suffixed name (`idx_<plainTable>___row_<view>` hashed via `toPostgresIdentifierWithHash`) to survive Postgres's 63-char identifier limit.

### Decisive source
```ts
const adjacentOrder =
  adjacentResult.rows.length > 0
    ? adjacentResult.rows[0]!.order_val
    : position === 'before'
      ? anchorOrder - 1      // inserting past the end extends the range
      : anchorOrder + 1;

const gap = Math.abs((anchorOrder - adjacentOrder) / (count + 1));
if (gap < Number.EPSILON * 2) {
  await this.shuffleRecords(dynamicDb, tableName, orderColumnName); // ROW_NUMBER() renumber 1..N
  const retry = await this.calculateOrders(context, table, viewId,
    anchorId, position, count);                                      // exact integers again
  if (retry.isErr()) return err(retry.error);
  return ok(retry.value);
}

const base = position === 'before' ? adjacentOrder : anchorOrder;
return ok(Array.from({ length: count }, (_, i) => base + gap * (i + 1)));
```

**Flow:** ensure the view's order column exists (ALTER TABLE + backfill from `__auto_number` + CREATE INDEX IF NOT EXISTS, all idempotent) → read the anchor's order value (missing anchor ⇒ `not_found` error) → read the adjacent neighbor in the requested direction (none ⇒ synthesize `anchor ± 1`) → midpoint math assigns K strictly-increasing values between anchor and neighbor → if the gap collapsed below float resolution, renumber the WHOLE view with `ROW_NUMBER()` (dense integers restore huge gaps) and recurse once.
**Invariant:** returned values are strictly ordered between the neighbors (before-anchor inserts land BELOW the anchor: base = adjacent, ascending away from it); float exhaustion is repaired by rebalancing, not by failing or corrupting order; the order column is additive metadata — dropping it never affects row data, and multiple views coexist as independent columns.
**Probe:** `packages/v2/adapter-table-repository-postgres/src/record/repository/PostgresRecordOrderCalculator.pglite.spec.ts::"creates order column and calculates values before anchor"` (:195), `::"returns not-found when anchor is missing"` (:240), `::"creates distinct order indexes for long table names and multiple views"` (:263).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable",
  query: "calculateOrders shuffleRecords ensureOrderColumnExists", limit: 10,
  fields: ["signature", "name", "file"] });
```

## Verdict
Adopt fractional midpoint ordering with per-consumer lazy columns and a dense renumber escape hatch — it works on vanilla Postgres without extensions. Adapt the column-naming scheme, the seed source, and the epsilon threshold to host precision needs; consider `numeric`/bigint strategies if you need exact decimals. Omit teable's view/viewId coupling if you need only one sort key. Caveat: file is parse_partial at single lines 52/70/78/129 (template-literal SQL) — excerpts were verified against raw source at HEAD.
