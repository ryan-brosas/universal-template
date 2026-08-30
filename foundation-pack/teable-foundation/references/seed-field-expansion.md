<!-- capsule-v2 -->
# Seed-field expansion — why must changed-field sets grow before planning, and how are formula-only dependencies caught?

## union(changed ∪ computed-fields-depending-on-changed); formula AST fallback when dependency metadata lies
**Path/Symbol:** `PostgresTableRecordRepository.ts` — `expandComputedSeedFieldIds(table, changedFieldIds)` (:3893–3932), call sites :2032/:2119/:2317/:2607/:2887/:3733; companion capsules `computed-update-planner`, `insert-pruning-seeding`.
**Signature:** `(table, changedFieldIds): core.FieldId[]`.

### Decisive source
```ts
const seedFieldIds = new Map<string, core.FieldId>(changedFieldIds.map(id => [id.toString(), id]));
const changedSet = new Set(seedFieldIds.keys());
for (const field of table.getFields()) {
  if (!field.computed().toBoolean()) continue;
  let dependsOnChangedField = field.dependencies()
    .some(depId => changedSet.has(depId.toString()));
  if (!dependsOnChangedField && field instanceof core.FormulaField) {
    const refsResult = field.expression().getReferencedFieldIds();   // AST fallback
    if (refsResult.isOk())
      dependsOnChangedField = refsResult.value.some(id => changedSet.has(id.toString()));
  }
  if (dependsOnChangedField) seedFieldIds.set(field.id().toString(), field.id());
}
return [...seedFieldIds.values()];
```

**Flow:** start from literally-changed fields → add every COMPUTED field whose declared dependencies intersect them → formula fields get a second chance via parsing their expression AST for referenced ids → return the deduped union as the seed set the planner topo-sorts.
**Invariant:** The expansion happens at the REPOSITORY layer (before enqueue AND before inline planning) because both lanes need identical seeds; missing an indirect dependency means a computed cell stays stale until an unrelated write touches it — silent data corruption, no error anywhere. The AST fallback exists because `dependencies()` metadata can lag the expression after formula edits (meta drift theme); it runs ONLY for FormulaField instances where the typed dependency list is least trustworthy. Link fields are excluded from insert-seed widening upstream (:3585–3587) but never from this function — link-triggered recomputation must still seed dependent rollups/lookups.
**Probe:** deterministic grep :3916–3923 (AST fallback); exercised by every hybrid/async suite via plan inputs.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "expandComputedSeedFieldIds getReferencedFieldIds dependencies", limit: 5 });
```
## Verdict
Adopt: any write-triggered derived-data system needs a single choke-point expander that unions direct changes with metadata-derived dependents plus an AST fallback for drift-prone declarations.
