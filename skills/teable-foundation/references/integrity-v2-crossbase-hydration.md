<!-- capsule-v2 -->
# Cross-base hydration closure — why does base-scoped integrity repair need tables from OTHER bases loaded first?

**Source:** teable AGPL `develop@06a4461e`; Codebase Memory `teable`. **Question:** How does the v2 service prevent valid cross-base lookups from being flagged/repaired as broken?

## loadReferencedForeignTables family
**Path/Symbol:** `apps/nestjs-backend/src/features/integrity/integrity-v2.service.ts:loadReferencedForeignTables` (:458–488) → `collectReferencedForeignTables` (:491–504), `collectFieldReference` (:506–541), `registerReferencedTable` (:542–568), `loadTablesByIds` (:589–632); consumed by `resolveSchemaTarget` :285 and `resolveBaseTarget` :342.
**Signature:** `loadReferencedForeignTables(tables, tableRepository, context): Promise<ReadonlyArray<Table>>`.
**Data Shape:** `IReferencedForeignTables = { byBase: Map<baseId,{baseId,tableIds:Set}>, unknownBase: Set<tableId> }`.

### Decisive source
```ts
if (references.unknownBase.size > 0) {
  const fallbackBaseId = tables[0]?.baseId();
  if (fallbackBaseId) {
    await this.loadTablesByIds(
      tableRepository, context, fallbackBaseId,
      [...references.unknownBase], tablesById, true   // withoutBaseId=true
    );
  }
}
```
(Base attribution falls back to the LINK FIELD's base when the lookup field itself has none:)
```ts
const [linkField] = table.getFields((c) => c.id().toString() === linkFieldId);
this.registerReferencedTable(references, tablesById, foreignTableId,
  linkField ? this.getFieldBaseId(linkField) : undefined);
```

**Flow:** Walk every field of every target table → derive foreignTableId (+ owning base via field or its link twin; else unknownBase) → batch-load per foreign base with `Table.specs(base).byIds(...)` under `activeWithPending` state → unknown-base leftovers retry against the FIRST table's base using `withoutBaseId()` specs (cross-base tables live in another schema, so the spec must not constrain baseId). Direct test `integrity-v2.service.spec.ts:325+` proves the repair stream that marked fields `hasError` becomes EMPTY once the foreign table is hydrated (`expect(tableRepository.find.mock.calls[0]?.[2]).toEqual({ state: 'activeWithPending' })`, `repairedContextResults).toEqual([])`).
**Invariant:** Repair decisions are made against metaTables = original + closure; skipping the closure makes the checker see a missing foreign table and "repair" (mark hasError) VALID lookups — the exact regression the spec pins. Duck-typed capability probes (`typeof candidate.foreignTableId === 'function'`) tolerate mixed Field implementations.
**Probe:** `grep -cF 'unknownBase' apps/nestjs-backend/src/features/integrity/integrity-v2.service.ts` → 5; `grep -cF 'activeWithPending' <same>` → 2.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "loadReferencedForeignTables unknownBase registerReferencedTable", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt closure-before-verdict hydration with unknown-base fallback specs; adapt spec/repository calls; omit the duck-typing if your Field type is sealed.
