<!-- capsule-v2 -->
# sqlite-init-phase-pipeline — how do I initialize/migrate/reset an embedded DB so every step is transactional, retryable, and re-runnable without nuking live account data?

**Source:** lh-basis (Linked Helper extract) **NO LICENSE — learn-only, patterns recorded, zero code copied**; Codebase Memory `lh-basis-source` (root `…/core/local-source/dist/Source`, minified single-line files — line spans collapse to `3-3`; symbol-level retrieval is the anchor). **Question:** how does a production LinkedIn-automation core structure database bootstrap so a crash mid-upgrade leaves a consistent, re-runnable schema?

## Ordered phase pipeline + destructive-op choreography
**Path/Symbol:** `Source/Source/SqliteSource.js:SqliteSource.initPhases / resetDBPhases / clearDB / dropDB` (queued); `DB/Init/DBInitPhase.js:DBInitPhase.executePhases` (static driver, default `transactionBehavior="IMMEDIATE"`); `DB/Init/common/QueriesExecutionPhase.js` (query lists + REVERSED transformation stack).
**Signature:** `initPhases` getter → ordered phase instances; `DBInitPhase.executePhases(core, phases, type, retryDelay=200, maxRetries=3)`; `SqliteMigratePhase({core, role, migrations, retryDelay, maxRetries, instanceProfileData})`.
**Data Shape:** each phase = `{transaction: bool, transactionBehavior: 'IMMEDIATE'|'EXCLUSIVE'|…, exec()}`; the pipeline composes named query batches: VersioningPhaseQueries → MigratePhase → TablesCreationPhaseQueries (≈120 CREATE TABLE modules) → SetInstanceProfilePhase → FillTablesByDefaultValuesQueries (+ LiAccountDependentValues) → Drop+Create Views (`setTransactionBehavior("EXCLUSIVE")`) → TableLogsPhase → TriggersCreationPhaseQueries → OptimizePhase.

### Decisive source
```js
// SqliteSource.clearDB — wipe DATA, never SCHEMA: FKs off, triggers/views dropped,
// tables emptied in REVERSE sqlite_master order skipping the version table
await this.core.exec("PRAGMA foreign_keys = OFF;");
for (const t of dbTriggerNames) await this.core.exec(`DROP TRIGGER ${t};`);
for (const v of dbViewNames)   await this.core.exec(`DROP VIEW ${v};`);
const tables = (await this.core.all("SELECT name FROM sqlite_master WHERE type='table'"))
  .reverse().map(r => r.name);
for (const t of tables)
  if ("version" !== t) await this.core.exec(`DELETE FROM ${t};`);
await DBInitPhase.executePhases(this.core, this.resetDBPhases, this.type,
                                this.retryDelay, this.maxRetries);
await this.core.exec("PRAGMA foreign_keys = ON;");
// dropDB — structural drop is ONE multi-statement exec inside execInTransaction
let sql = ""; for (const t of dbTableNames) sql += `DROP TABLE ${t};`;
await this.core.exec(sql);
// both decorated: __decorate([Source.queued], SqliteSource.prototype, "clearDB"/"dropDB")
```

**Flow:** source construction → constructor enqueues `DBInitPhase.executePhases(… initPhases …)` on the SAME per-source action queue as business calls (bootstrap can never interleave with an account action) → each phase runs under `retryOnBusy(_executeInTransaction(core, level, phase.exec))` with default IMMEDIATE behavior → migration phase replays the ordered migrations list with its own retry knobs → reset path (`clearDB`) empties data then re-runs only fill/view/trigger/log/profile phases via `resetDBPhases`.
**Invariant:** every phase is idempotent-or-transactional so a crash mid-pipeline replays cleanly; the `version` table survives data resets (schema-version state is load-bearing); reverse-order deletion respects FK dependencies while FK enforcement is explicitly OFF; views are rebuilt under EXCLUSIVE because DROP+CREATE VIEW cannot be transactional in SQLite; destructive ops (`clearDB`/`dropDB`) go through the same queued decorator as reads/writes — they serialize against account activity by construction.
**Probe:** no public tests (proprietary dist extract) — coverage caveat recorded. Byte-exact probes anchored at `lh-basis/core/local-source/dist`: `grep -c "PRAGMA foreign_keys" Source/Source/SqliteSource.js` ⇒ 2 (OFF + ON, one minified line — occurrence count via `grep -o | wc -l`; `grep -c` yields 1); `grep -c "type='table'" Source/Source/SqliteSource.js` ⇒ 1; `grep -c '"version"!==t' Source/Source/SqliteSource.js` ⇒ 1; `grep -c 'reverse()' Source/Source/SqliteSource.js` ⇒ 1; `grep -c 'setTransactionBehavior("EXCLUSIVE")' Source/Source/SqliteSource.js` ⇒ 1; `grep -c '__decorate' Source/Source/SqliteSource.js` ⇒ 1 covering BOTH queued methods (`grep -o 'queued\],SqliteSource.prototype,"[a-zA-Z]*"' | sort -u` ⇒ clearDB, dropDB).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "lh-basis-source", query: "clearDB dropDB SqliteSource", limit: 5 });
// rank#1/#2: Source.SqliteSource.SqliteSource.clearDB / .dropDB (Source/SqliteSource.js 3-3), PostgresSource twins next
```

## Verdict
Adopt the shape: bootstrap as an ordered list of small transactional-retryable phases executed through the SAME serialization queue as business traffic; reset-data-vs-drop-schema as two distinct operations where reset preserves the version row and rebuilds derived objects. Adapt phase granularity to your migration tool. Omit the product-specific table inventory (~120 tables) and license-gated feature plumbing. **No-license repo: patterns only, zero code copied.**
