<!-- capsule-v2 -->
|# up/down statement duality — why does every DDL op execute AND return {upStatement, downStatement}, and what breaks when the two halves drift?

**Source:** nocodb (Sustainable Use License) `develop@640fe3b06fb26c9d000e2258477001c0d5e62c73`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-nocodb`. **Question:** What is the shape and ordering contract of the Result-wrapped DDL return across all dialect clients?

## up-down statement duality
**Path/Symbol:** `packages/nocodb/src/db/sql-client/lib/KnexClient.ts:tableRename` (:943–978), `indexCreate` (:1131–1193), `indexDelete` (:1204–1261), `relationCreate` (:1272–1334), `relationDelete` (:1346–1410); `querySeparator()` :1841–1843.
**Signature:** every DDL method returns `Result{ data.object = { upStatement: [{sql}], downStatement: [{sql}] } }`; executed SQL is `this.querySeparator() + query.toQuery()` where separator = `'/* xc */\n'`.
**Data Shape:** arrays of `{sql}` frames — multiple statements per frame allowed (joined with the separator), order = execution order.

### Decisive source
```ts
// KnexClient.tableRename :952–971 — EXECUTE then EMIT the pair:
await this.sqlClient.raw(this.sqlClient.schema.renameTable(args.tn_old,args.tn).toQuery());
const upStatement = this.querySeparator() + this.sqlClient.schema.renameTable(...).toQuery();
const downStatement = this.querySeparator() + this.sqlClient.schema.renameTable(args.tn,args.tn_old).toQuery();
result.data.object = { upStatement: [{ sql: upStatement }], downStatement: [{ sql: downStatement }] };

// relationDelete :1354–1385 — the SURPRISE: delete executes BOTH directions
await this.sqlClient.raw(query.toQuery());            // dropForeign (the actual delete)
await this.sqlClient.raw(downQuery.toQuery());        // ← RE-CREATES the FK it just dropped!
// (base-class quirk; PgClient.relationDelete :1135–1190 correctly executes only the drop)
```
Asymmetric flag twins — create keys on `non_unique`, delete keys on `non_unique_original`: indexCreate `if (args.non_unique) table.index(...) else table.unique(...)`; indexDelete `if (args.non_unique_original) table.dropIndex(...) else table.dropUnique(...)`. MysqlClient.indexList :782 preserves both (`non_unique_original = non_unique`) precisely so the delete twin can round-trip.

**Flow:** build knex schema builder → toQuery() → execute raw → rebuild the SAME builder for up + its inverse for down → prefix each with `/* xc */\n` → return in Result. Callers (migrator/meta layer) persist these frames so a failed multi-step operation can roll back statement-by-statement. The separator comment doubles as a split marker for hosts that must replay statements individually.

**Invariant:** (1) Up/down are built from SEPARATE builder invocations, never string-derived by reversal — dialect-specific SQL (IF EXISTS placement, identifier quoting) differs between directions. (2) Down-order is reverse-dependency: PgClient.tableDelete assembles dropTable THEN re-create-FKs-then-indexes into ONE down frame in dependency order (tables first, then the FKs and indexes that reference them); porters who reorder them produce unexecutable downs. (3) The non_unique/non_unique_original twin is load-bearing: dropping an index you created as UNIQUE via dropIndex fails on some engines — the ORIGINAL kind decides the drop verb. (4) Base-class relationDelete's double-execution is a recorded trap — do not "fix" it silently when subclassing; PG overrides it.

**Probe:** runner BLOCKED (no upstream unit specs import sql-client) → deterministic probes at pin: `sed -n '1346,1385p' packages/nocodb/src/db/sql-client/lib/KnexClient.ts | grep -c 'raw'` = 2 (both executions present — the drop at :1360 and the re-create at :1381; range :1346–1365 holds only one); `grep -n 'non_unique_original' packages/nocodb/src/db/sql-client/lib/mysql/MysqlClient.ts` resolves :782 usage; `grep -n "xc \*/" packages/nocodb/src/db/sql-client/lib/KnexClient.ts` pins the separator literal (:1842).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-nocodb", query: "upStatement downStatement relationDelete indexCreate KnexClient", limit: 10 });
```

## Verdict
Adopt execute-plus-return-pair shape, separate builder invocations per direction, and the original-kind flag twin for unique drops; adapt separator marker and Result envelope to host; omit the legacy double-execution relationDelete path (treat PG override as canonical).
