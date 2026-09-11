<!-- capsule-v2 -->
|# sqlite table-update machine — why must column edits become rename-copy-drop, which PRAGMAs flip around the transaction, and how does the quote-aware splitter keep multi-statements safe?

**Source:** nocodb (Sustainable Use License) `develop@640fe3b06fb26c9d000e2258477001c0d5e62c73`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-nocodb`. **Question:** What is the exact SqliteClient.tableUpdate choreography, and which SQLite quirks does each step neutralize?

## sqlite table-update machine
**Path/Symbol:** `packages/nocodb/src/db/sql-client/lib/sqlite/SqliteClient.ts:tableUpdate` (:1547–1764), `alterTableColumn` rename-copy-drop (:2150–2255), dependent-index sweep (:1633–1652), `splitQueries` (:1674–1709), `alterTablePK` object-return twin (:2073–2111), `genValue` override (:2293–2299).
**Signature:** `alterTableChangeColumn(t, n, o, existingQuery)` emits FOUR statements: RENAME old→`{cno}_nc_{suffix}` → ADD new → `UPDATE t SET new = {cno}_{suffix}` → DROP renamed; suffix = nanoid(6) over `[1-9a-z_]`.
**Data Shape:** PRAGMA result rows are plain arrays (knex sqlite returns rows directly, NOT `[rows,fields]`); `alterTablePK` returns `{newPks, oldPks, dropPks}` or false — consumed by trx.schema.alterTable, never stringified.

### Decisive source
```ts
// :1629–1632 — dependent-index sweep, verbatim comment:
// SQLite refuses `ALTER TABLE ... DROP COLUMN` (SQLITE_ERROR) while a user-created
// index references the column ... `origin = 'c'` keeps implicit UNIQUE/PK autoindexes untouched.
SELECT DISTINCT il.name FROM pragma_index_list(?) il JOIN pragma_index_info(il.name) ii
WHERE il.origin='c' AND ii.name IN (${dropped.map(()=>'?').join(', ')})
// → DROP INDEX IF EXISTS ?? for each, PREPENDED to upQuery.

// :1654–1670 — PRAGMA choreography + the documented hack:
if (fkCheckEnabled) await raw('PRAGMA foreign_keys = OFF;');
await raw('PRAGMA legacy_alter_table = ON;');
// This is a hack to avoid SQLITE_ERROR duplicate-column-name when we drop a column and
// add a new column with the same name right after it. TODO - Find a better solution.
await this.sqlClient.raw('SELECT * FROM ?? LIMIT 1', [args.table]);
const trx = await this.sqlClient.transaction();

// splitQueries — quote-state machine: toggles 'double'|'single' mode, counts CLOSING quotes,
// skips escaped (prev==='\\'), splits ONLY on ';' while quotationCount % 2 === 0.

// finally (:1742–1746): foreign_keys restored ON iff it was on; legacy_alter_table ALWAYS OFF.
```
Down-query asymmetry (:1596/:1612): col-edit and col-add append `';'` as a NO-OP down statement — sqlite ALTER cannot express the inverse, so rollback of edits is structurally unsupported (downStatement frames are `';'` throughout tableCreate/tableDelete too).

**Flow:** collect altered columns by bitmask (remove guarded by `!pk`) → build four-step copy ladder per edited column (nanoid suffix avoids name collision with the incoming name) → prepend index drops for every dropped/renamed-away column → snapshot fk pragma, turn FK off + legacy ON → warm the table (duplicate-name hack) → open ONE explicit transaction → replay split statements through trx.raw → apply pk diff via knex schema builder INSIDE the same trx → commit → restore pragmas in finally → afterTableUpdate re-adds xc_trigger_ AFTER UPDATE triggers keyed on the FIRST pk column (`pk = args.columns.find(c=>c.pk)`, early-return without one).

**Invariant:** (1) The rename-copy-drop ladder is mandatory because stock SQLite ALTER COLUMN doesn't exist — porters emitting MODIFY/ALTER COLUMN produce runtime syntax errors. (2) PRAGMA restore pairing is asymmetric BY DESIGN: legacy_alter_table unconditionally OFF, foreign_keys only if it was ON — flipping FK on for connections that ran with it off changes host semantics. (3) splitQueries must be quote-aware or trigger bodies containing ';' (xc_trigger BEGIN...END blocks from afterTableCreate) shatter mid-statement. (4) Index drops filter origin='c' — dropping autoindexes would strip PK/UNIQUE enforcement permanently. (5) genValue lets bare CURRENT_TIMESTAMP through UNQUOTED (quoted timestamps are rejected as defaults in older sqlite); everything else binds. (6) hasTable probes by SELECTing the table and catching the error — information_schema-style lookups don't exist.

**Probe:** runner BLOCKED (no upstream spec imports SqliteClient) → deterministic probes at pin: `sed -n '1663,1669p' packages/nocodb/src/db/sql-client/lib/sqlite/SqliteClient.ts` shows the hack comment verbatim; `grep -c "PRAGMA" packages/nocodb/src/db/sql-client/lib/sqlite/SqliteClient.ts` ≥ 7; `grep -n "_nc_" packages/nocodb/src/db/sql-client/lib/sqlite/SqliteClient.ts` pins the rename-suffix sites :2158/:2187/:2193.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-nocodb", query: "SqliteClient tableUpdate splitQueries legacy_alter_table alterTableColumn", limit: 10 });
```

## Verdict
Adopt the four-statement copy ladder, origin-filtered index sweep, quote-aware splitter, and the exact PRAGMA enter/exit pairing; adapt suffix minting and pk-diff plumbing to host; omit down-migration support for sqlite edits (structurally impossible without table rebuild).
