<!-- capsule-v2 -->
# Junction-table rule family — how is a many-to-many link's storage rebuilt from surviving JSONB link values, and when does repair refuse or demand confirmation?

**Source:** teable AGPL `develop@06a4461e`; Codebase Memory `teable`. **Question:** What is the create/validate/backfill contract for junction tables, including the missing-host-schema and orphan-rows manual paths?

## JunctionTableExistsRule + children (unique/index/FK)
**Path/Symbol:** `packages/v2/adapter-table-repository-postgres/src/schema/rules/field/JunctionTableRule.ts` — `JunctionTableExistsRule` (:129–647), `JunctionTableUniqueConstraintRule` (:651–723, constraint `uniq_${selfKeyName}_${foreignKeyName}`), `JunctionTableIndexRule` (:727–772, index `index_${columnName}`), `JunctionTableForeignKeyRule` (:776–1251); backfill SQL in `rules/helpers/StatementBuilders.ts` `backfillJunctionTableFromLinkValueStatement`; diagnostics `rules/helpers/ForeignKeyDiagnostics.ts`.
**Signature:** `static createRulesFromField(field, config): ISchemaRule[]` → `[exists, unique, (indexes if withIndexes), fkSelf, fkForeign]`; config = `{junctionTable, selfKeyName, foreignKeyName, orderColumnName?, sourceTable, foreignTable, foreignTableMetaId?, withIndexes?}`.
**Data Shape:** junction shape `__id serial PK, selfKey text, foreignKey text [, order double precision]`; validation failures carry stable codes: `junction_table_host_schema_missing`, `junction_table_foreign_target_missing`, `junction_foreign_key_orphan_rows`.

### Decisive source
```sql
-- up() backfill: rebuild ONLY rows still derivable from the stored JSONB link column,
-- preserving ordinality for the order column; skip flag compiled in as literal TRUE/FALSE
WITH pairs AS (
  SELECT s."__id" AS self_id, elem.value->>'id' AS foreign_id, elem.ord AS order_pos
  FROM <source> AS s
  CROSS JOIN LATERAL jsonb_array_elements(
    CASE WHEN jsonb_typeof(col)='array' THEN col
         WHEN jsonb_typeof(col)='null' THEN '[]'::jsonb
         ELSE jsonb_build_array(col) END) WITH ORDINALITY AS elem(value, ord)
), dedup AS (SELECT self_id, foreign_id, MIN(order_pos) FROM pairs GROUP BY 1,2)
INSERT INTO <junction> (...) SELECT ... FROM dedup d
WHERE NOT EXISTS (SELECT 1 FROM <junction> j WHERE j.self=d.self AND j.foreign=d.foreign);
```

**Flow:** isValid ladder = host schema exists? → table exists? → target table resolvable via metaId (`resolveTableIdentifierByMetaId`: query `table_meta` on the META db, fall back to declared identifier, return undefined when meta table itself is absent) → required columns exist. Repair routing: host schema missing ⇒ MANUAL form ('create the schema') because auto-repair can't invent a schema; target table missing ⇒ hint `available:false` (nothing to do); FK missing + equivalent-FK-by-columns exists ⇒ valid; FK missing + orphan count>0 ⇒ MANUAL 'delete_orphan_rows' form; else plain auto `up()`. Partial tables are healed by per-column ADD COLUMN IF NOT EXISTS (skipped under `optimizeForEmptyTables`). Shared-column links (`sameColumnLinkFieldCount > 1`) compile the backfill to a no-op.
**Invariant:** recovery source of truth is ALWAYS the persisted link-value column — repairs restore only relations still derivable from it and say so verbatim in their hint text; `down()` is a single DROP TABLE CASCADE.
**Probe:** `packages/v2/adapter-table-repository-postgres/src/schema/rules/field/SchemaRules.pglite.spec.ts:2038 'should return invalid when junction table does not exist'`, :2055 host-schema-missing manual hint, :2079 manual create+rebuild round-trip, :2106 'should not auto repair...when the foreign table is missing', :2208 backfill-from-link-value.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "JunctionTableExistsRule resolveTableIdentifierByMetaId backfillJunctionTableFromLinkValueStatement", limit: 10 });
```

## Verdict
Adopt coded validation failures driving repair routing, meta-id→physical-name resolution with graceful absence, JSONB-as-recovery-source backfill, and shared-column skip flags; adapt naming conventions (junction_/uniq_/index_ prefixes); omit the i18n message bodies.
