<!-- capsule-v2 -->
# Three-way schema diff — how do you compute a destructive-safe DDL plan from the live DB?

**Source:** Strapi MIT Expat (non-EE) `develop@1fd9d80ad5f0a2c97d09ce7529f5cd9fdb91ca2d`; Codebase Memory `strapi`. **Question:** When your in-memory schema is the source of truth, how do you diff it against a live database without dropping tables/columns you never created?

## 3-way diff: DB schema × previous tracked schema × new user schema
**Path/Symbol:** `packages/core/database/src/schema/diff.ts` : `diffSchemas` (388–485), `diffTables` (368–386), `diffTableColumns` (215–260), `diffTableIndexes` (262–306).
**Signature:** `diffSchemas(ctx: SchemaDiffContext): Promise<SchemaDiff>` with `ctx = { previousSchema?, databaseSchema, userSchema }`; per-object comparators return `{ status: 'CHANGED'|'UNCHANGED', diff }`.
**Data Shape:** output `{ status, diff: { tables: { added, updated, unchanged, removed } } }`; `updated` entries carry nested column/index/FK diffs.

### Decisive source
```ts
for (const databaseTable of databaseSchema.tables) {
  const isInUserSchema = helpers.hasTable(userSchema, databaseTable.name);
  const wasTracked = previousSchema && helpers.hasTable(previousSchema, databaseTable.name);
  const isReserved = reservedTables.includes(databaseTable.name);

  // NOTE: if db table is not in the user schema and is not in the previous stored
  // schema leave it alone. it is a user custom table that we should not touch
  if (!isInUserSchema && !wasTracked) {
    continue;
  }
  if (!isInUserSchema && wasTracked && !isReserved) {
    // ... collect dependencies from persisted_tables dependsOn ...
    removedTables.push(databaseTable, ...dependencies);
  }
}
```

**Flow:** forward pass — for each user-schema table: exists in DB? then `diffTables` (columns+indexes+FKs sub-diffs folded via `hasChangedStatus`) else `added`. Reverse pass — for each DB table not in user schema: remove **only if** the previous tracked schema also had it and it isn't reserved; cascade-attach tables listed in its persisted `dependsOn`. Column/index removal uses the identical previous-tracking guard (`!hasColumn(user) && previousTable && hasColumn(previous)`).
**Invariant:** nothing is ever removed because it is merely *unknown* — removal requires positive evidence that this layer tracked the object before. This single rule is what makes auto-sync at boot safe next to plugin-created or user-created tables.
**Probe:** `src/schema/__tests__/schema-diff.test.ts:172–203` ('UnTracked Table' → UNCHANGED, empty removed); `:1161–1214` ('With persisted DB tables' → only the previously-tracked table is removed).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "strapi", query: "schema diff synchronize changes", limit: 30, fields: ["lines", "signature"] });
// returned diffSchemas @ diff.ts 388-485, diffTables @ 368-386, diffTableColumns @ 215-260, diffTableIndexes @ 262-306
```

## Verdict
Adopt the three-input diff shape and the "tracked-or-it-survives" removal guard for any declarative schema manager. Adapt the reserved-table list and the core-store `persisted_tables`/`dependsOn` lookup to your host's extension registry. Omit the EE→CE audit-log special case. Coverage: all cited paths `no_recorded_issue`, metadata_match.
