<!-- capsule-v2 -->
# mysql/sqlite extractor twins — how do ER_* codes and SQLITE_* message-parsing mirror the PG table, and where do the dialects structurally differ?

**Source:** NocoDB Sustainable Use License `develop@640fe3b06fb26c9d000e2258477001c0d5e62c73`; Codebase Memory project `mnt-hdd-utopia-inspo-platforms-nocodb`. **Question:** What does a porter need to know to replicate the MySQL and SQLite legs of the error-extraction table without inventing message shapes that don't exist in source?

## ER_* ladder (mysql.extractor.ts) + message-shape ladder under one code (sqlite.extractor.ts)

**Path/Symbol:** `packages/nocodb/src/helpers/db-error/mysql.extractor.ts:MysqlDBErrorExtractor.extract` (:13–195); `packages/nocodb/src/helpers/db-error/sqlite.extractor.ts:SqliteDBErrorExtractor.extract` (:13–146).
**Signature:** identical `extract(error): DBErrorExtractResult` contract; both return `{error: NcErrorType.ERR_DATABASE_OP_FAILED, message, code, httpStatus}` — note NEITHER mysql nor sqlite spreads `details` into the result (unlike pg), so `_extra` computed there is dead weight at the wire.
**Data Shape:** mysql switches on driver codes (`ER_TRUNCATED_WRONG_VALUE`, `ER_TABLE_EXISTS_ERROR`, `ER_DUP_FIELDNAME`, `ER_NO_SUCH_TABLE`, `ER_DUP_ENTRY`, `ER_BAD_NULL_ERROR`, `ER_DATA_TOO_LONG`, `ER_WARN_DATA_OUT_OF_RANGE`, `ER_BAD_FIELD_ERROR`, `ER_ACCESS_DENIED_ERROR`, `ER_LOCK_WAIT_TIMEOUT`, `ER_LOCK_DEADLOCK`, …); sqlite has only ~8 real codes (`SQLITE_BUSY`, `SQLITE_CONSTRAINT`, `SQLITE_CORRUPT`, `SQLITE_MISMATCH`, `SQLITE_ERROR`, `SQLITE_RANGE`, `SQLITE_SCHEMA`) so specificity comes from MESSAGE regexes.

### Decisive source
```ts
// sqlite :54-115 — one code, seven message shapes, ordered
const noSuchTableMatch        = error.message.match(/no such table: (\w+)/);
const tableAlreadyExistsMatch = error.message.match(/SQLITE_ERROR: table `?(\w+)`? already exists/);
const duplicateColumnExists   = error.message.match(/SQLITE_ERROR: duplicate column name: (\w+)/);
const unrecognizedTokenMatch  = error.message.match(/SQLITE_ERROR: unrecognized token: "(\w+)"/);
const columnDoesNotExistMatch = error.message.match(/SQLITE_ERROR: no such column: (\w+)/);
const constraintFailedMatch   = error.message.match(/SQLITE_ERROR: constraint failed: (\w+)/);
```

**Flow (mysql):** type-mismatch codes parse `Incorrect (\w+) value: (.+) for column '(\w+)'`; existence codes parse `Table '?(\w+)'? already exists` / `Duplicate column name '(\w+)'` / `Table '(?:\w+\.)?(\w+)' doesn't exist` (schema-qualified tolerated) / `Unknown column '(\w+)' in 'field list'`; ER_DUP_ENTRY is generic ("This record already exists." — NO detail parsing here, unlike pg); ER_ACCESS_DENIED_ERROR→403, ER_LOCK_WAIT_TIMEOUT→500, ER_LOCK_DEADLOCK→409; unknown code → log + generic 500 + return. **Flow (sqlite):** SQLITE_BUSY/CORRUPT→500; SQLITE_CONSTRAINT joins matched FOREIGN KEY/UNIQUE tokens into the message (`match(/FOREIGN KEY|UNIQUE/gi)?.join(' ')` or fallback `'constraint'`) and sets UNIQUE_CONSTRAINT_VIOLATION only when `/UNIQUE/i` matches; SQLITE_ERROR runs the six-way regex chain above in a strict else-if order with a final `/SQLITE_ERROR:\s*(\w+)/` single-word fallback.
**Invariant:** (1) The sqlite else-if ORDER is semantic: "no such table" must precede the generic word-extraction fallback or every message collapses to its first word. (2) mysql's default branch RETURNS early (generic message + 500), skipping the common return tail — same shape as pg. (3) Both extractors guard `if (!error.code) return;` first so the dispatch trial-ladder can skip them on foreign errors.

### Porting traps (each verified against source)
- The `EACCES` case appears in BOTH mysql (:175–178) and sqlite (:125–128) ladders with the SSRF message 'Connection to internal hosts is not allowed' → 403 — it is the SAME cross-dialect SSRF marker as pg's EACCES (:348–351).
- In-file anchors: `grep -c "case 'ER_DUP_ENTRY'" src/helpers/db-error/mysql.extractor.ts` → 1; `grep -c "case 'ER_ACCESS_DENIED_ERROR'" …` → 1; `grep -c 'SQLITE_ERROR' src/helpers/db-error/sqlite.extractor.ts` → 7; `grep -c 'SQLITE_CONSTRAINT' …` → 1; `grep -c 'httpStatus = 409' src/helpers/db-error/mysql.extractor.ts` → 1.

**Probe:** Deterministic probe from repo root:
`cd packages/nocodb && grep -n 'FOREIGN KEY|UNIQUE' src/helpers/db-error/sqlite.extractor.ts | head -1` → line `30:` region and `sed -n '30,41p' src/helpers/db-error/sqlite.extractor.ts | grep -c "join(' ')"` → `1`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-nocodb", query: "MysqlDBErrorExtractor SqliteDBErrorExtractor extract", limit: 10 });
```
Resolves both extractor classes rank-1/rank-2 (`has_more: true`).

## Verdict
Adopt the per-dialect code tables verbatim as compatibility surfaces, keep sqlite's message-shape ordering, and preserve the no-details wire shape for these two legs (or consciously upgrade all three together); adapt messages to host; omit nothing silently. Coverage caveat: no direct tests at pin; probes are source-greps.
