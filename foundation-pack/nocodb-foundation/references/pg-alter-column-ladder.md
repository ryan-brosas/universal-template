<!-- capsule-v2 -->
|# pg alter-table column ladder — how does one method emit RENAME/TYPE/NULL/DEFAULT/AI/UNIQUE for Postgres, and which diffs are silently destructive if mis-ordered?

**Source:** nocodb (Sustainable Use License) `develop@640fe3b06fb26c9d000e2258477001c0d5e62c73`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-nocodb`. **Question:** What exact statement sequence does PgClient.alterTableColumn produce per change mode, and what invariants govern the AI (auto-increment) and unique transitions?

## pg alter-table column ladder
**Path/Symbol:** `packages/nocodb/src/db/sql-client/lib/pg/PgClient.ts:alterTableColumn` (:3157–3432) with change modes 0=createTableColumn/:3130, 1=alterTableAddColumn/:3134, 2=alterTableChangeColumn/:3138; orchestrator `tableUpdate` :2559–2731; PK diff `alterTablePK` :3044–3112.
**Signature:** `alterTableColumn(n, o, existingQuery, change = 2, softDeleteColumnName?)` — n=new column meta, o=old; returns concatenated SQL text (multi-statement, `;`-separated).
**Data Shape:** column objects carry `{cn, cno, dt, uidt, dtxp, rqd, cdf, ai, unique, pk, tn, internal_meta?}`; tn may be schema-qualified.

### Decisive source
```ts
// change===2 rename guard — prevents ACCIDENTAL renames (:3249–3254):
const columnName = newColumnName && newColumnName !== oldColumnName ? newColumnName : oldColumnName;
if (oldColumnName && newColumnName && oldColumnName !== newColumnName)
  query += genQuery(`\nALTER TABLE ?? RENAME COLUMN ?? TO ?? ;\n`, [t, oldColumnName, newColumnName], true);

// type change: DROP DEFAULT → optional dateConversionFunction → TYPE ... USING cast (:3273–3318)
if (n.dt !== o.dt) {
  query += genQuery(`\nALTER TABLE ?? ALTER COLUMN ?? DROP DEFAULT;\n`, ...);
  if ([UITypes.Date,DateTime,Time,Duration].includes(n.uidt))
    query += pgQueries.dateConversionFunction.default.sql;          // helper fn must exist FIRST
  query += genQuery(`\nALTER TABLE ?? ALTER COLUMN ?? TYPE ${sanitiseDataType(n.dt)} USING `, ...);
  // AutoNumber backfill overwrites all values → plain `0::bigint`; else generateCastQuery(format/durationType)
}

// AI add: sequence OWNED BY the column, default via regclass STRING with inner double quotes (:3340–3360)
query += genQuery(`\nCREATE SEQUENCE IF NOT EXISTS ?? OWNED BY ??.??;\n`, [seqName, t, n.cn], true);
query += genQuery(`\nALTER TABLE ?? ALTER COLUMN ?? SET DEFAULT nextval(?);\n`, [t, n.cn, seqRegclass], true);

// AI removal trap, verbatim comment :3368–3372:
// `serial` is `NOT NULL DEFAULT nextval(...)`, but it is added via the n.ai branch which never
// emits a NOT NULL clause — so metadata keeps rqd=false and the rqd-diff can't see the constraint.
// Dropping the default without it leaves a NOT NULL column that nothing populates.
} else if (!n.ai && o.ai) {
  query += genQuery(`... DROP DEFAULT;\n`, ...);
  if (!n.rqd) query += genQuery(`\nALTER TABLE ?? ALTER COLUMN ?? DROP NOT NULL;\n`, ...);
}
```

**Flow:** tableUpdate iterates columns by `altered` bitmask (4=remove→`DROP COLUMN IF EXISTS`, 2|8=edit→change ladder, 1=add→ADD + deferred unique), pre-resolving missing unique-constraint names into `oldColumn.internal_meta.unique_constraint_name` via queryUniqueConstraintName BEFORE the ladder runs; alterTablePK appends `<table>_pkey` drop/add only when pk sets actually differ. Unique transitions route through addUniqueConstraintToQuery: drop constraint IF EXISTS + schema-qualified `DROP INDEX IF EXISTS`, then either partial unique index (`WHERE (softCol IS NULL OR softCol = false)` — skipped for pk/ai columns) or `ADD CONSTRAINT ... UNIQUE`.

**Invariant:** (1) Statement ORDER inside change===2 is contractual: RENAME first, then type (whose USING expression references the NEW name), then nullability, then default, then AI, then unique — reordering makes later statements reference not-yet-existing names. (2) The serial NOT NULL asymmetry means AI-add never emits NOT NULL but AI-remove MUST conditionally drop it — porters who "symmetrize" the pair break inserts after AI conversion. (3) nextval's argument binds as a STRING containing `"schema"."seq"` (regclass literal), not an identifier bind. (4) DROP INDEX must be schema-qualified or non-default search_path schemas silently miss (recorded comment :3409–3413 → subsequent CREATE fails "already exists"). (5) Partial unique index is gated on softDeleteColumnName presence AND ¬pk ∧ ¬ai — PK/autoincrement keep unconditional constraints.

**Probe:** runner BLOCKED (no upstream unit specs import PgClient; jest testRegex `(Integration|Source)\.spec\.ts$` matches none under db/) → deterministic probes at pin: `sed -n '3368,3372p' packages/nocodb/src/db/sql-client/lib/pg/PgClient.ts` shows the serial-NOT-NULL comment verbatim; `grep -c 'IF EXISTS' packages/nocodb/src/db/sql-client/lib/pg/PgClient.ts` ≥ 6; `grep -n "OWNED BY" packages/nocodb/src/db/sql-client/lib/pg/PgClient.ts` resolves :3352 single site.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-nocodb", query: "PgClient alterTableColumn addUniqueConstraintToQuery queryUniqueConstraintName", limit: 10 });
```
(graph resolved `PGClient.alterTableColumn` line-exact 3157–3432.)

## Verdict
Adopt the fixed statement order, the accidental-rename guard, OWNED-BY sequence minting, and the AI-removal NOT NULL compensation; adapt cast generation to host type system; omit the mssql/oracle equivalents unless porting those dialects.
