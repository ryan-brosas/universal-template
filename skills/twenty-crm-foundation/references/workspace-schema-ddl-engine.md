<!-- capsule-v2 -->
# workspace-schema-ddl-engine

## Source
- Repo: `twenty-crm`
- Path: `packages/twenty-server/src/engine/twenty-orm/workspace-schema-manager/services/workspace-schema-table-manager.service.ts`
- Symbol: `WorkspaceSchemaTableManagerService` (createTable / dropTable / renameTable)
- Lines: 8-67 (whole class)
- Commit: `a6eedd8bf2afad74b6c9a68c9ccaa06d3ce753a0`
- Graph Node: `ext-twenty-crm.packages.twenty-server.src.engine.twenty-orm.workspace-schema-manager.services.workspace-schema-table-manager.service.WorkspaceSchemaTableManagerService.createTable`

## Signature & Data Shape
```typescript
export class WorkspaceSchemaTableManagerService {
  createTable(args: {
    queryRunner: QueryRunner;
    schemaName: string;      // workspace schema namespace, e.g. "workspace_1ab2..."
    tableName: string;
    columnDefinitions?: WorkspaceSchemaColumnDefinition[];
  }): Promise<void>;
  dropTable(args: { queryRunner; schemaName; tableName; cascade?: boolean }): Promise<void>;
  renameTable(args: { queryRunner; schemaName; oldTableName; newTableName }): Promise<void>;
}
```

## Decisive Source Excerpt
```typescript
const sqlColumnDefinitions =
  columnDefinitions?.map((columnDefinition) =>
    buildSqlColumnDefinition(columnDefinition),
  ) || [];

if (sqlColumnDefinitions.length === 0) {
  sqlColumnDefinitions.push('"id" uuid PRIMARY KEY DEFAULT gen_random_uuid()');
}

const sql = `CREATE TABLE IF NOT EXISTS ${escapeIdentifier(schemaName)}.${escapeIdentifier(tableName)} (${sqlColumnDefinitions.join(', ')})`;
await queryRunner.query(sql);

// dropTable:
const cascadeClause = cascade ? ' CASCADE' : '';
const sql = `DROP TABLE IF EXISTS ${escapeIdentifier(schemaName)}.${escapeIdentifier(tableName)}${cascadeClause}`;

// renameTable — note the ASYMMETRY:
const sql = `ALTER TABLE ${escapeIdentifier(schemaName)}.${escapeIdentifier(oldTableName)} RENAME TO ${escapeIdentifier(newTableName)}`;
```

## Flow
1. Column fragments come from `buildSqlColumnDefinition`: `escapeIdentifier(name)` + enum-mapped type (+ `[]` for arrays) + optional `GENERATED ALWAYS AS (tsvector expression)` guarded by `assertSafeTsVectorExpression`, PRIMARY KEY / NOT NULL flags, and a pre-serialized DEFAULT.
2. Empty definition list falls back to a canonical `"id" uuid PRIMARY KEY DEFAULT gen_random_uuid()` column so every tenant table has a stable PK.
3. Schema AND table identifiers go through `escapeIdentifier` at the string-template sink; statements are idempotent (`IF [NOT] EXISTS`) to survive retry/race across concurrent nodes during rolling upgrades.
4. Foreign keys, indexes, views, and enum types live in companion manager services in the same folder following the same shape.

## Invariant
Every multi-tenant DDL statement must (a) escape BOTH schema and table identifiers with PG-standard quoting, (b) be idempotent with IF EXISTS/IF NOT EXISTS so concurrent node retries converge, and (c) guarantee a primary key even when metadata supplies no columns. The rename path is the trap: `RENAME TO <new>` takes the new name UNQUALIFIED but still quoted — porters habitually schema-qualify it and ship invalid SQL.

## Direct-Test Probe
The service has no dedicated spec (coverage caveat); behavior is pinned indirectly through its composed utils:

```bash
grep -n "CREATE TABLE IF NOT EXISTS\|gen_random_uuid" packages/twenty-server/src/engine/twenty-orm/workspace-schema-manager/services/workspace-schema-table-manager.service.ts   # => :30,:33
grep -cn "describe('escapeIdentifier'" packages/twenty-server/src/engine/workspace-manager/workspace-migration/utils/__tests__/remove-sql-injection.util.spec.ts   # => 1 (:17)
```

- Related spec: `packages/twenty-server/src/engine/twenty-orm/workspace-schema-manager/utils/__tests__/sanitize-default-value.util.spec.ts` (:15) covers the DEFAULT pre-serialization feeding this builder.

## Graph Query
```bash
echo '{"project":"ext-twenty-crm","name_pattern":"WorkspaceSchemaTableManagerService"}' | codebase-memory-mcp cli search_graph
```

## Verdict
Adopt the sanitized idempotent workspace-DDL trio together with `buildSqlColumnDefinition`; do not port one without the other or the tsvector/DEFAULT guards are lost.
