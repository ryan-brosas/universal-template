<!-- capsule-v2 -->
# busy-retry-transaction-kernel — how do I run writes against a shared embedded SQLite DB without SQLITE_BUSY crashes or half-applied multi-statement batches?

**Source:** lh-basis (Linked Helper extract) **NO LICENSE — learn-only, patterns recorded, zero code copied**; source-read plane `core/local-source/dist/helpers/{sql.js,functions.js}` — OUTSIDE every Codebase Memory project root (`lh-basis-source` stops at `dist/Source/`), so retrieval below is expected-empty; byte-exact file probes are the anchors. **Question:** what is the minimal retry/transaction/chunking kernel that keeps concurrent account automation from corrupting or deadlocking an embedded database?

## Retry + dual-platform transaction + chunked-insert kernel
**Path/Symbol:** `helpers/sql.js:retryOnBusy`, `_executeInTransaction{,SQLite,PG}`, `withSavepoint`, `_e`, `getDataChunksToInsertIntoTableByValues`, `getInNinFilter`, `toFuzzy`; `helpers/functions.js:executeAndRetry`.
**Signature:** `executeAndRetry(fn, delayMs, maxRetries, retryableCodes)` → generic bounded retry; `retryOnBusy(fn, delay, maxRetries)` = `executeAndRetry(fn, delay, maxRetries, ["SQLITE_BUSY"])`; `_executeInTransaction(dbType, core, level, fn)`; `withSavepoint(fn, {core, name})`.
**Data Shape:** retryable predicate matches `err.code` membership ONLY (string codes, e.g. `SQLITE_BUSY`) — message text is never inspected; transactions take an explicit level string; chunk builders split row arrays into ≤999-host-parameter pieces (`MAX_PARAMS_COUNT=999`, SQLite's hard limit).

### Decisive source
```js
// functions.js — the WHOLE retry policy: fixed-delay, code-list-gated, last attempt rethrows
async function executeAndRetry(fn, delay, maxRetries, retryableCodes) {
  for (let i = 0; i < maxRetries; i++) try { return await fn(); }
  catch (e) {
    if (retryableCodes.includes(e.code)) {
      if (i >= maxRetries - 1) throw e;
      await new Promise(r => setTimeout(r, delay)); continue;
    }
    throw e;                       // non-retryable NEVER sleeps
  }
}
// sql.js — platform SPLIT hides SQLite-only syntax behind one call site
async function _executeInTransactionSQLite(core, level, fn) {
  await core.run(`BEGIN ${level}`);            // DEFERRED | IMMEDIATE | EXCLUSIVE pass through RAW
  try { const r = await fn(); await core.run("COMMIT TRANSACTION"); return r; }
  catch (e) { throw await core.run("ROLLBACK"), e; }   // rollback THEN rethrow ORIGINAL error
}
async function _executeInTransactionPG(core, level, fn) {
  let stmt = level === "DEFERRED"
    ? "ISOLATION LEVEL READ COMMITTED"
    : "ISOLATION LEVEL REPEATABLE READ";       // SQLite levels mapped onto PG isolation
  await core.run(`BEGIN ${stmt}`); /* …same commit/rollback-rethrow shape… */
}
```

**Flow:** any write path → `retryOnBusy(() => _executeInTransaction(type, core, level, batch))`: BEGIN → run every statement → COMMIT; on `SQLITE_BUSY` sleep the fixed delay and replay the ENTIRE batch (never resume mid-way); on any other error roll back and surface the original error untouched. Nested risk regions wrap single operations in `withSavepoint(fn, {core, name: randomUUID()})` — SAVEPOINT on entry, RELEASE on success, ROLLBACK TO SAVEPOINT on failure, original error rethrown either way. Bulk inserts pre-split rows so parameters-per-statement stay ≤ `floor(999/columnCount)`; `IN (...)` filters with an EMPTY value list emit literal `TRUE`/`FALSE` instead of illegal `IN ()`.
**Invariant:** retry granularity is the whole transaction, and the retryable-code list is closed — everything else fails fast; a failed transaction leaves NO partial statements (rollback precedes the rethrow); the caller's error object identity survives (no wrapping). Escaping stays centralized in `_e` (null→NULL literal, Date→ISO-then-escape, NaN/±Infinity THROW `Invalid val`, bool→1/0) and `toFuzzy` escapes `%`/`_`/`/` with `ESCAPE '/'` so user text can't inject wildcards.
**Probe:** no public tests (proprietary dist extract) — coverage caveat recorded. Deterministic probes anchored at `lh-basis/core/local-source/dist`: `grep -c 'SQLITE_BUSY' helpers/sql.js` ⇒ 1; `grep -o 'ISOLATION LEVEL [A-Z ]*' helpers/sql.js | sort -u` ⇒ exactly READ COMMITTED + REPEATABLE READ; `grep -c 'includes(e.code)' helpers/functions.js` ⇒ 1; `grep -c 'Math.floor(999' helpers/sql.js` ⇒ 1; `grep -c "ESCAPE '/'" helpers/sql.js` ⇒ 1.

## Get live surrounding code
**Retrieve:**
```ts
// EXPECTED EMPTY: helpers/ is outside every indexed root (umbrella lh-basis carries no Function nodes here).
await mcp.codebase_memory.search_graph({ project: "lh-basis-source", query: "retryOnBusy SQLITE_BUSY", limit: 5 }); // total: 0 — by construction
```
Consumers ARE indexed: `search_graph({project:"lh-basis-source", query:"execInQueue queuePromise", limit:4})` resolves `Source.execInQueue` (Source/Source.js) — the queue that serializes the calls this kernel executes.

## Verdict
Adopt the contract shapes: closed retryable-code lists with fixed-delay full-batch replay, one transaction entry point that hides platform BEGIN-dialect differences, savepoint wrappers for nested risk regions, 999-parameter insert chunking, and empty-IN→TRUE/FALSE emission; adapt the level mapping to your ORM's API. Omit nothing conceptually, but **re-implement from scratch — this repo carries no license, so no code may be copied**.
