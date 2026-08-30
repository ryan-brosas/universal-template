<!-- capsule-v2 -->
# ActiveDoc Fetch Ladder — which storage answers a table query, and when must a read wait for formulas or clone before filtering?

**Source:** grist-core Apache-2.0 `main@b83224bbe9c88910dfeb28922df254a26f702f68`; Codebase Memory `grist-core`. **Question:** For one `fetchQuery` call against a live collaborative doc, what decides between SQLite-direct, engine, cached-engine, and filtered-metadata paths — and what must happen to shared cached data before row/column access rules are applied?

## fetchQuery decision ladder over (onDemand × snapshot × fullyLoaded × readPermission)
**Path/Symbol:** `app/server/lib/ActiveDoc.ts` — `fetchQuery` (:1401–1477), helpers `_fetchQueryFromDB` (:3302–3316), `_fetchQueryFromDataEngine` (:3318–3320); cache field `_fetchCache = new MapWithTTL(...DEFAULT_CACHE_TTL)` (:334).
**Signature:** `fetchQuery(docSession, query: ServerQuery, waitForFormulas = false): Promise<TableFetchResult>`.
**Data Shape:** input query sanitized to `{tableId, filters, limit}` only (`pick(query, [...])`, :1405) — an untrusted `where` part can never ride through; output `{tableData: TableDataAction, attachments?: BulkAddRecord}`.

### Decisive source
```ts
query = pick(query, ["tableId", "filters", "limit"]);
this._inactivityTimer.ping();     // reads keep the doc open
const tableAccess = await this._granularAccess.getTableAccess(docSession, query.tableId);
this._granularAccess.assertCanRead(tableAccess);
if (query.tableId.startsWith("_gristsys_")) { throw new Error("Cannot fetch _gristsys tables"); }
if (query.tableId.startsWith("_grist_") && !await this._granularAccess.canReadEverything(docSession)) {
  const tables = await this.fetchMetaTables(docSession);   // already ACL-filtered
  const tableData = tables[query.tableId];
  if (tableData) { return { tableData }; }                 // meta tables NEVER come raw from SQLite
}
const wantFull = waitForFormulas || query.tableId.startsWith("_grist_") ||
  this._granularAccess.getReadPermission(tableAccess) === "mixed";
const onDemand = this._onDemandActions.isOnDemand(query.tableId);
let data: TableDataAction;
if (onDemand || this._isSnapshot) {
  data = await this._fetchQueryFromDB(query, onDemand);            // SQL side, formula placeholders expanded
} else if (wantFull) {
  await this.waitForInitialization();
  data = await this._fetchQueryFromDataEngine(query);              // engine only, after full load
} else {
  if (!this._fullyLoaded) {
    data = await this._fetchQueryFromDB(query, false);             // early reader: DB with pending placeholders
  }
  if (this._fullyLoaded) {  // may have become true while fetching from DB
    const key = JSON.stringify(query);
    data = await mapGetOrSet(this._fetchCache, key, () => this._fetchQueryFromDataEngine(query));
  }
}
if (this._granularAccess.getReadPermission(tableAccess) !== "allow") {
  data = cloneDeep(data!);  // Clone since underlying fetch may be cached and shared.
  await this._granularAccess.filterData(docSession, data);
}
```

**Flow:** sanitize → ping inactivity timer → table-level access assert (`_gristsys_` never readable) → `_grist_` metadata requests under partial access are re-routed through the ACL-filtered `fetchMetaTables` view → branch: onDemand/snapshot ⇒ SQLite via `expandQuery` (formula columns become placeholders or constants substituted back at :3309–3314); full-needed ⇒ block on `_initializationPromise` then ask the Python engine; otherwise early readers get DB rows and post-load readers share a TTL'd promise cache keyed by the JSON of the query → if permission is `"mixed"` (row/column rules), deep-clone then filter; finally attachment columns referenced by the result trigger an `_grist_Attachments` metadata addendum (:1464–1472).
**Invariant:** (1) The engine-result cache is cleared wholesale on ANY successful modification (`this._fetchCache.clear()` inside `_applyUserActions`'s `result.isModification` branch, :2572) — a porter who caches without that invalidation serves stale reads after edits. (2) Filtered results must be cloned before mutation because the unfiltered object may be aliased by the shared cache or by another concurrent session's response. (3) `_gristsys_*` tables are unreachable through this surface regardless of session privileges.
**Probe:** direct tests `test/server/lib/ActiveDoc.ts`: `describe("fetchQuery")` (:385) including "should support querying for regular tables" (:516) and "should support querying for on-demand tables" (:523); "can access document before engine opens" (:1124) pins the pre-initialization DB path; granular-access suites `test/server/lib/GranularAccess.ts` pin `filterData` outcomes.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "grist-core",
  query: "ActiveDoc fetchQuery _fetchQueryFromDB onDemand", limit: 10,
  fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the four-way source ladder (SQL-with-placeholders / wait-then-engine / early-reader-SQL / shared TTL promise cache), the wholesale cache invalidation on any modification, and clone-before-filter discipline. Adapt cache TTL and key granularity to your host. Omit Grist's `_gristsys_`/`_grist_` naming conventions unless porting the schema itself. Caveat: the exact `mixed`-permission clone line has no dedicated unit test — it is exercised indirectly via GranularAccess suites.
