<!-- capsule-v2 -->
# Junction order-column write ladder — how are reordered link arrays persisted without losing per-source ordering?

**Source:** teable AGPL `develop@06a4461e`; Codebase Memory `teable`. **Question:** How does a ManyMany/OneMany link write distinguish "set membership changed" from "only order changed", and why?

## saveForeignKeyForManyMany / saveForeignKeyForOneMany
**Path/Symbol:** `apps/nestjs-backend/src/features/calculation/link.service.ts:saveForeignKeyForManyMany` (:1183–1308), `:saveForeignKeyForOneMany` (:1452–1603, one-way → delegates to ManyMany at :1457–1461), `:getMaxOrderForTarget` (:1309–1330).
**Signature:** `saveForeignKeyForManyMany(field: LinkFieldDto, fkMap: {[recordId]: IFkRecordItem})`.
**Data Shape:** Junction rows `(selfKeyName, foreignKeyName[, orderColumnName])`; `getHasOrderColumn()` gates all order logic; `getOrderColumnName()` names the `<fk>_order` column.

### Decisive source
```ts
// Check if only order has changed (same elements but different order)
const hasOrderChanged =
  oldKey.length === newKey.length &&
  oldKey.length > 0 &&
  newKey.length > 0 &&
  oldKey.every((key) => newKey.includes(key)) &&
  newKey.every((key) => oldKey.includes(key)) &&
  !oldKey.every((key, index) => key === newKey[index]);

if (hasOrderChanged) {
  // For order changes only: delete all and re-insert in correct order
  toDeleteAndReinsert.push([recordId, newKey]);
}
```
(Append-only adds keep per-source monotonic order:)
```ts
currentMaxOrder = await this.getMaxOrderForTarget(...); // MAX(order) per source, null→0
...
data[linkField.getOrderColumnName()] = currentMaxOrder + i + 1;
```

**Flow:** Same-set-different-order ⇒ DELETE all junction rows for that source then re-INSERT in requested order with `order = index+1`. Add/remove deltas ⇒ differential delete (`whereIn([self,foreign], pairs)`) + grouped inserts where each source's first new row starts at `MAX(order)+1`. OneMany (FK-on-foreign-table variant): reorder clears the FK columns of every old child and batch-updates each child with its new index; plain adds append after `MAX(self_key_order)` for that target. OneMany without an order column updates ONLY rows whose FK actually changes (in-source comment).
**Invariant:** Order is a FIRST-CLASS stored attribute — set-based diffing alone would silently scramble user-visible link order; conversely the full delete+reinsert must fire ONLY when membership is unchanged, else it churns rows. `Number(raw)` coercion with null→0 keeps aggregates safe across drivers.
**Probe:** `grep -cF 'hasOrderChanged' apps/nestjs-backend/src/features/calculation/link.service.ts` → 4 (both ladders + two comments); `grep -cF '.forUpdate()' <same>` → 1 (PG-only SELECT…FOR UPDATE guard in `lockForeignRecords` :1424).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "saveForeignKeyForManyMany order column junction getMaxOrderForTarget", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the three-way classification (delete+reinsert on pure reorder / differential on membership change / append-after-MAX on adds) plus PG-gated foreign-record locking; adapt order-column naming; omit teable's LinkFieldDto accessors in favor of your field-model equivalents.
