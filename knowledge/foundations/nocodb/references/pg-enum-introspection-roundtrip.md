<!-- capsule-v2 -->
|# pg enum introspection round-trip — how does columnList capture a native enum's identity, and how do findColumnsUsingType + internal_meta make in-place ALTER TYPE safe?

**Source:** nocodb (Sustainable Use License) `develop@640fe3b06fb26c9d000e2258477001c0d5e62c73`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-nocodb`. **Question:** How does the pg client learn which columns share a user-defined type, and what metadata must survive the round-trip for option add/rename to touch the type instead of cell data?

## pg enum introspection round-trip
**Path/Symbol:** `packages/nocodb/src/db/sql-client/lib/pg/PgClient.ts:columnList` USER-DEFINED branch (:812–987, enum binding :948–966), `findColumnsUsingType` (:1004–1050); consumer: `services/formula-column-type-changer.service.ts` family (option add/rename on native enums).
**Signature:** `findColumnsUsingType({typeSchema, typeName, excludeTableSchema?, excludeTableName?, excludeColumnName?}): Promise<{table_schema, table_name, column_name}[]>`.
**Data Shape:** columnList emits `internal_meta = { pg_enum_type_name, pg_enum_schema_name }` ONLY when `udt_typtype === 'e'` AND both udt_name and udt_schema are present.

### Decisive source
```ts
// :955–965 — partial metadata is REJECTED by design (comment verbatim :950–954):
// Bind the column to its native PG enum type so columnUpdate can emit ALTER TYPE
// for option add/rename instead of touching cell data. Both name and schema are
// captured (the enum can live in a different schema from the table) and we require
// both — partial metadata would force callers to guess the schema later.
if (column.udt_typtype === 'e' && response.rows[i].udt_name && response.rows[i].udt_schema) {
  column.internal_meta = { ...(column.internal_meta || {}),
    pg_enum_type_name: response.rows[i].udt_name,
    pg_enum_schema_name: response.rows[i].udt_schema };
}
```
```sql
-- findColumnsUsingType :1032–1048 — catalog-level reference scan:
SELECT n_tbl.nspname AS table_schema, cls.relname AS table_name, attr.attname AS column_name
FROM pg_attribute attr
JOIN pg_class cls       ON cls.oid = attr.attrelid
JOIN pg_namespace n_tbl ON n_tbl.oid = cls.relnamespace
JOIN pg_type typ        ON typ.oid = attr.atttypid
JOIN pg_namespace n_typ ON n_typ.oid = typ.typnamespace
WHERE n_typ.nspname = ? AND typ.typname = ?
  AND cls.relkind IN ('r','p')          -- ordinary + partitioned tables only
  AND attr.attnum > 0                   -- skip system columns
  AND NOT attr.attisdropped             -- skip dropped columns
  [AND NOT (n_tbl.nspname=? AND cls.relname=? AND attr.attname=?)]  -- all-three-or-none exclusion
```
The columnList query itself joins `pg_enum/pg_type/pg_namespace` twice per row to fetch `string_agg(enumlabel)` as `enum_values` and `typtype` as `udt_typtype`, version-gating an `is_identity` selector on `majorVersion >= 10` parsed from `SELECT version()` (:817–827).

**Flow:** introspect → columns of typtype 'e' carry their type identity into internal_meta → UI edits options → caller runs findColumnsUsingType (excluding ITSELF via the three-arg exclusion so self-reference never blocks) → sole owner ⇒ mutate type in place with ALTER TYPE; shared ⇒ fork a new type and rebind this column only.

**Invariant:** (1) The exclusion triple is atomic — passing one or two of the three exclude args silently scans nothing-excluded (hasExclude requires ALL THREE); callers must pass the trio or none. (2) relkind must include 'p' (partitioned) or shared-type detection misses partitioned tables and an "in-place" ALTER TYPE breaks siblings. (3) internal_meta flows through the meta layer as possibly-stringified JSON — every consumer re-parses defensively (`typeof === 'string' → JSON.parse → catch {}`) before reading unique_constraint_name/pg_enum keys; assuming an object crashes on round-tripped rows. (4) Enum VALUES for display come from the same query's enum_values subselect — never re-query per option render.

**Probe:** runner BLOCKED (no upstream spec covers PgClient) → deterministic probes at pin: `sed -n '950,965p' packages/nocodb/src/db/sql-client/lib/pg/PgClient.ts` shows comment+guard; `grep -c "attisdropped" packages/nocodb/src/db/sql-client/lib/pg/PgClient.ts` ≥ 1 (single findColumnsUsingType site); graph resolved `PGClient.findColumnsUsingType` at :1004–1050 line-exact.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-nocodb", query: "findColumnsUsingType pg_enum_type_name udt_typtype internal_meta", limit: 10 });
```

## Verdict
Adopt the both-fields-required internal_meta binding, the relkind r/p + attnum/attisdropped scan predicates, and the atomic exclusion trio; adapt the meta key names to host conventions but keep defensive string-parse on read.
