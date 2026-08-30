<!-- capsule-v2 -->
# FK column DDL restoration — how do you recreate missing junction/FK columns with the RIGHT constraint shape per relationship?

**Source:** teable AGPL `develop@06a4461e`; Codebase Memory `teable`. **Question:** What exact ALTER/CREATE does each relationship need when its FK storage vanished, and which errors are tolerable?

## fixMissingForeignKeyColumns
**Path/Symbol:** `apps/nestjs-backend/src/features/integrity/link-integrity.service.ts:fixMissingForeignKeyColumns` (:482–685).
**Signature:** `fixMissingForeignKeyColumns(fieldId, issueType?): Promise<IIntegrityIssue|undefined>`.
**Data Shape:** Branch inputs: host table exists?, selfKey/foreignKey/orderColumn existence (parallel probes), relationship enum, OneOne FK-is-`__id` special case.

### Decisive source
```ts
if (options.relationship === Relationship.OneOne && options.foreignKeyName === '__id') {
  // Symmetric OneOne fields do not own the FK column.
  return;
}
...
case Relationship.ManyOne:
case Relationship.OneOne: {
  if (!foreignKeyExists) {
    table.string(options.foreignKeyName).references('__id').inTable(foreignDbTableName)
      .withKeyName(`fk_${options.foreignKeyName}`);
    if (options.relationship === Relationship.OneOne) {
      table.unique([options.foreignKeyName], { indexName: `index_${options.foreignKeyName}` });
    }
  }
```
```ts
} catch (error) {
  if (error instanceof Prisma.PrismaClientKnownRequestError &&
      error.code === 'P2010' &&
      (error.meta as { code?: string })?.code === '42P07') {
    // Relation already exists; continue with the rest of the fix
    continue;
  }
  throw error;
}
```

**Flow:** Resolve field + dbTableName + foreign dbTableName → symmetric-OneOne-owns-nothing early-out → host MISSING ⇒ full create via `createColumnSchema`; host present ⇒ per-column ALTER adding exactly what's missing WITH constraints shaped by relationship (ManyMany both sides get FK references; OneOne adds UNIQUE; one-way OneMany gets composite unique on (self,foreign); order columns always nullable integers) → PRAGMA statements filtered (SQLite) → 42P07 already-exists swallowed → ALWAYS finish with `backfillForeignKeysFromLinkColumn`.
**Invariant:** Constraint shapes must match what the DDL path would have created (unique on OneOne FK, composite pair-unique on one-way OneMany) or later writes will violate/duplicate. 42P07 tolerance makes re-runs idempotent; any OTHER error still aborts. The backfill tail is unconditional — a restored column without data backfill leaves links silently broken.
**Probe:** `grep -cF '42P07' apps/nestjs-backend/src/features/integrity/link-integrity.service.ts` → 1; `grep -cF 'PRAGMA' <same>` → 2.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "fixMissingForeignKeyColumns createColumnSchema alterTable", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt existence-diffed DDL repair with relationship-exact constraints + idempotent error tolerance + mandatory backfill; adapt knex schema calls; omit the OneOne `__id` carve-out if your model differs.
