<!-- capsule-v2 -->
# Custom-SQL endpoint confinement — how do you expose arbitrary SELECTs on an embedded database without turning it into an injection surface?

**Source:** grist-core (Apache-2.0), `main@b83224bbe9c88910dfeb28922df254a26f702f68`; Codebase Memory `grist-core`. **Question:** Which layers actually confine user-supplied SQL, and which are cosmetic?

## runSQLQuery defense ladder
**Path/Symbol:** `app/server/lib/runSQLQuery.ts:runSQLQuery` (23-93), `MAX_CUSTOM_SQL_MSEC` (10-18).
**Signature:** `runSQLQuery(requestOrSession: NonNullable<RequestOrSession>, activeDoc: ActiveDoc, options: Types.SqlPost): Promise<ResultRow[]>` with `options = { sql: string, args?: any[], timeout?: number }`.
**Data Shape:** Timeout knob via appSettings: env `GRIST_SQL_TIMEOUT_MSEC`, default **1000ms**, clamped `Math.max(0, Math.min(MAX, param || MAX))`. Wrapper capability facts come from `docStorage.getOptions()` (`MinDBOptions`).

### Decisive source
```ts
if (!(await activeDoc.canCopyEverything(docSession))) {
  throw new ApiError("insufficient document access", 403);          // L1 authz
}
const statement = options.sql.replace(/;$/, "");
// A very loose test, just for early error message
if (!statement.toLowerCase().includes("select")) {
  throw new ApiError("only select statements are supported", 400); // L2 sniff (cosmetic)
}
if (!sqlOptions?.canInterrupt || !sqlOptions?.bindableMethodsProcessOneStatement) {
  throw new ApiError("The available SQLite wrapper is not adequate", 500); // L3 capability
}
const wrappedStatement = `select * from (${statement})`;           // L5 grammar pin
const interrupt = setTimeout(async () => {
  try { await activeDoc.docStorage.interrupt(); } catch (e) { log.error(...); }
}, timeout);                                                        // L4 time fence
try { return await activeDoc.docStorage.all(wrappedStatement, ...(options.args || [])); }
finally { clearTimeout(interrupt); }
```

**Flow:** Authz (must be able to read everything ⇒ 403) → strip ONE trailing semicolon + lowercase `includes("select")` as an EARLY-FEEDBACK heuristic only → hard-refuse unless the driver declares `canInterrupt` AND `bindableMethodsProcessOneStatement` → clamp timeout → wrap text in `select * from (...)` forcing SQLite onto the SELECT grammar branch → arm a `setTimeout` calling the driver's `interrupt()` → run `all(...)`, clearing the timer in `finally`. The safety argument (in-source comment, 58-75): bindable methods process only the FIRST statement (node-sqlite3 puts the rest in an ignored "tail string"), so a `Robert'); DROP TABLE Students;--` suffix is inert; wrapping alone is NOT sufficient ("straightforward to break out... with multiple statements") — the first-statement-only property carries the guarantee.
**Invariant:** Never advertise the keyword sniff as security — confinement = capability-verified wrapper (first-statement-only) + grammar-pin wrap + interrupt deadline + copy-level authz. If a host driver cannot declare those capability bits, the endpoint must refuse (Grist returns 500 rather than degrading).
**Probe:** No dedicated upstream test for the endpoint (coverage caveat). The wrapper shapes it rides on are pinned by `test/server/lib/DocStorageQuery.ts` (allMarshal call-shape assertions :26-79). Deterministic anchors: `grep -n "bindableMethodsProcessOneStatement\|select \* from (" app/server/lib/runSQLQuery.ts` → hits at :44/:46/:76.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "grist-core", query: "runSQLQuery", limit: 5 });
```
## Verdict
Adopt the five-layer ladder (authz → soft sniff → capability gate → clamp+interrupt → grammar pin) for any "raw SQL read" feature on an embedded engine; adapt the capability-flag vocabulary to your driver interface; omit the node-sqlite3 tail-string lore once your driver provably single-statements.
