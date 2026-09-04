<!-- capsule-v2 -->
# Reference-plane rules — how are field dependency edges stored as meta rows with delete-vs-convert asymmetry, and what else rides the meta plane?

**Source:** teable AGPL `develop@06a4461e`; Codebase Memory `teable`. **Question:** How do reference/meta rules keep computed-field dependency edges truthful during deletion vs conversion, and which rules bypass the data schema entirely?

## ReferenceRule + FieldMetaRule + SelectOptionsMetaRule
**Path/Symbol:** `packages/v2/adapter-table-repository-postgres/src/schema/rules/field/ReferenceRule.ts` whole (182L); `field/FieldMetaRule.ts` up/down (:131–167); `field/SelectOptionsMetaRule.ts` — choice token map (:224–262), `repairStoredChoiceValues` (:264–329).
**Signature:** `ReferenceRule.single/multiple(field, fromFieldId(s), {fieldType, required})`; all three set `validationScope='meta'` so checker/repairer swap ctx.db→ctx.metaDb for their isValid.
**Data Shape:** reference row = `{id: getRandomString(25), to_field_id (dependent), from_field_id (dependency)}`; uniqueness on `(to_field_id, from_field_id)` via ON CONFLICT DO NOTHING; FieldMeta patches are flat string-keyed jsonb.

### Decisive source
```ts
// DELETE vs CONVERT asymmetry — the invariant that keeps dependent fields alive:
down(ctx) {
  if (ctx.mode === 'delete') {
    // permanent removal: clean edges BOTH directions
    return ok([metaStatement(ctx.metaDb.deleteFrom('reference')
      .where(eb => eb.or([eb.eb('to_field_id','=',fId), eb.eb('from_field_id','=',fId)])))]);
  }
  // update/convert default: remove only INBOUND edges (to_field_id),
  // preserving outbound (from_field_id) so dependents keep cascade paths
  return ok([metaStatement(ctx.metaDb.deleteFrom('reference').where('to_field_id','=',fId))]);
}
// select-options repair maps stale tokens → canonical names, id-priority:
ORDER BY CASE WHEN e.id = c.old_id THEN 0 ELSE 1 END  // match by id first, name second
```

**Flow:** factory emits one ReferenceRule per dependency family (formula deps, rollup link+lookup+condition+sort ids, lookup link/lookup pair with optional non-required link edge) → isValid checks each expected pair exists in meta `reference` table → up inserts with conflict-do-nothing; conversion regenerates references by running oldRules' ReferenceRule.down + newRules' .up in place (`regenerateFieldReferences`, TableSchemaUpdateVisitor :448–504). Meta statements compile against the UNSCOPED db (`db.withoutPlugins()` as metaDb in visitors; pglite spec pins compiled SQL contains `'update "field"'` and NOT `"schema"."field"`). FieldMeta up MERGES keys via `(coalesce(meta::jsonb,'{}') || patch)` and down subtracts exactly its own keys.
**Invariant:** meta rules NEVER qualify table names with the base schema even when ctx.db is schema-scoped; repair rewrites stored CELL values only where they point at removed duplicate choices (never touching unrelated options keys); optimizeForEmptyTables skips both meta repairs (duplicate/import persists aggregates up front).
**Probe:** `packages/v2/adapter-table-repository-postgres/src/schema/rules/field/SchemaRules.pglite.spec.ts:2612 'keeps metadata statements outside the scoped data schema'`, :2717 'merge metadata updates instead of overwriting unrelated keys', :2957 'remap single-select values that point at removed duplicate choices', :3028 multi-select dedup remap.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "ReferenceRule validationScope meta FieldMetaRule repairStoredChoiceValues choice_token_map", limit: 10 });
```

## Verdict
Adopt directed reference rows with delete/convert down() asymmetry, merge-don't-overwrite meta patches, id-before-name canonicalization of select choices, and unconditional meta-plane scoping; adapt the meta table inventory to host; omit i18n detail items.
