<!-- capsule-v2 -->
|# mysql unique-as-index + alter ladder — how do MySQL's CHANGE COLUMN and index-backed uniqueness shape the edit path, and which response-shape quirks hide in columnList?

**Source:** nocodb (Sustainable Use License) `develop@640fe3b06fb26c9d000e2258477001c0d5e62c73`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-nocodb`. **Question:** What does MysqlClient.alterTableColumn emit per mode, why is DROP INDEX the only way to remove a UNIQUE constraint, and what does tableDelete's down-migration capture that pg's cannot?

## mysql unique-as-index + alter ladder
**Path/Symbol:** `packages/nocodb/src/db/sql-client/lib/mysql/MysqlClient.ts:alterTableColumn` (:2668–2748), `addUniqueConstraintToQuery`/`getUniqueConstraintName`/`queryUniqueConstraintName` (:2537–2666), `tableUpdate` sanitize wrap (:2211–2219), `tableDelete` show-create-table down (:2244–2283), `columnList` timestamp DEFAULT_GENERATED recombination (:659–678), `schemaCreate` func-key bug (:1392–1400).
**Signature:** `alterTableColumn(n, o, existingQuery, change=2)` — change 0 inline-create / 1 ADD COLUMN / 2 `CHANGE COLUMN ?? ?? <type>` (old+new name both required even for pure edits).
**Data Shape:** precision appended from `dtxp/dtxs` unless dt endsWith('text'); `un` → UNSIGNED; unique constraint names capped at 64 chars (vs pg's 63).

### Decisive source
```ts
// :2740–2743 — dropping a unique constraint = dropping its INDEX (verbatim comment):
// Use DROP INDEX to drop the unique constraint. MySQL stores unique constraints as indexes.
query += this.genQuery(`, DROP INDEX ??`, [constraintName]);
// addUniqueConstraintToQuery :2657–2663 — same doctrine on the add side:
// Note: MySQL uses DROP INDEX for unique constraints
query += genQuery(`, DROP INDEX ??`, [constraintName]) + genQuery(`, ADD CONSTRAINT ?? UNIQUE (??)`, ...);

// :2211–2218 — accumulated fragments re-bound as ONE identifier-carried statement:
upQuery = this.genQuery(`ALTER TABLE ?? ${this.sanitize(upQuery)};`, [args.tn]);
// (fragments contain literal '?' from bound values — sanitize() escapes them before the outer bind)

// tableDelete down :2256–2263 — MySQL can regenerate DDL verbatim:
createStatement = Object.entries(createStatement[0][0]).find(([k]) => k.toLowerCase() === 'create table')[1];
const downQuery = this.querySeparator() + createStatement;   // SHOW CREATE TABLE output AS-IS
```
columnList quirks: int/tinyint/mediumint/bigint/enum/set take dtxp by SUBSTRINGING column_type between parens (:707–712); timestamp/datetime defaults recombine cdf with the EXTRA column when it contains DEFAULT_GENERATED (:662–671) so `current_timestamp() ON UPDATE current_timestamp()` survives introspection; ai detected via ext.indexOf('auto_increment'); au forced false (:719 — MySQL needs no trigger-based updated-at).

**Flow:** tableUpdate iterates bitmask-altered columns; edited columns emit one `CHANGE COLUMN old new type(precision[,scale]) UNSIGNED NOT NULL auto_increment DEFAULT …` inside a comma-joined ALTER TABLE whose whole body was sanitized then re-bound against `??`; unique transitions resolve real INDEX_NAME from INFORMATION_SCHEMA.STATISTICS (`NON_UNIQUE = 0`) into internal_meta before emitting drops. PK changes append `,DROP PRIMARY KEY` + `,ADD PRIMARY KEY(...)`.

**Invariant:** (1) Unique-constraint lifecycle MUST go through index verbs — `DROP CONSTRAINT` doesn't exist for MySQL unique keys; porters using generic SQL fail at runtime. (2) The whole-body sanitize-then-bind means fragment-level binds are preserved as literals while the TABLE NAME stays parameterized — forgetting the inner sanitize turns data `?` into extra bind slots (bind-count mismatch). (3) CHANGE COLUMN requires BOTH names: passing only new name silently renames; only old name loses edits to nullability. (4) text types never take precision parens — appending them produces invalid DDL. (5) tableDelete's down is the SERVER's own DDL snapshot (captures engine/charset/auto_increment exactly); reimplementing it from columnList loses those. (6) schemaCreate copies `this.triggerList.name` into its func key (:1393) — works today ONLY because queries.schemaCreate.default exists and no versioned key is ever consulted; copying this pattern breaks any func with version-specific SQL.

**Probe:** runner BLOCKED (no upstream spec imports MysqlClient) → deterministic probes at pin: `grep -n "stores unique constraints as indexes" packages/nocodb/src/db/sql-client/lib/mysql/MysqlClient.ts` resolves :2741; `sed -n '1392,1400p' packages/nocodb/src/db/sql-client/lib/mysql/MysqlClient.ts` shows the triggerList func-key copy; `grep -c "DEFAULT_GENERATED" packages/nocodb/src/db/sql-client/lib/mysql/MysqlClient.ts` = 3 (:662/:667/:668).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-nocodb", query: "MysqlClient alterTableColumn addUniqueConstraintToQuery tableDelete", limit: 10 });
```

## Verdict
Adopt index-verb unique lifecycle, whole-body sanitize+bind composition, SHOW-CREATE-TABLE downs, and the DEFAULT_GENERATED recombination; adapt precision handling to host type vocabulary; fix (never copy) the schemaCreate func-key aliasing.
