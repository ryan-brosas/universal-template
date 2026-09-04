<!-- capsule-v2 -->
# History prune ladder — when does an ever-growing action log get trimmed without risking unshared work?

**Source:** grist-core (Apache-2.0), `main@b83224bbe9c88910dfeb28922df254a26f702f68`; Codebase Memory `grist-core`. **Question:** How do you bound rows+bytes of an append-only history cheaply, and what may never be deleted?

## _pruneLargeHistory / deleteActions
**Path/Symbol:** `app/server/lib/ActionHistoryImpl.ts:_pruneLargeHistory` (659-719), `deleteActions` (445-460), options block (20-40).
**Signature:** `private async _pruneLargeHistory(actionNum: number): Promise<void>` / `public async deleteActions(keepN: number): Promise<void>`.
**Data Shape:** Knobs via appSettings env flags: `GRIST_ACTION_HISTORY_MAX_ROWS` (default 1000), `GRIST_ACTION_HISTORY_MAX_BYTES` (default 1e9); fixed in code: graceFactor **1.25**, checkPeriod **10**. Checks read `count(*)` + `sum(length(body))` over the **shared chain only**.

### Decisive source
```ts
// Phase 0: amortize — size check only every checkPeriod actions
if (actionNum % this._options.checkPeriod !== 0) { return; }
// Phase 1: quick aggregate over the shared chain (never local work)
const checks = (await this._fetchParts(null, branches.shared,
  "count(*) as count, sum(length(body)) as bytes", undefined, true))[0];
if (checks.count <= this._options.maxRows * this._options.graceFactor &&
    checks.bytes <= this._options.maxBytes * this._options.graceFactor) {
  return; // Nothing to do, size is ok.
}
// Phase 2 inside execTransaction: walk newest→oldest, find FIRST overflow
for (let i = 0; i < rows.length; i++) {
  const row = rows[i]; count++; bytes += row.bytes;
  if (count > 1 && (bytes > this._options.maxBytes || count > this._options.maxRows)) {
    first = i; break;
  }
}
// Delete [first..end] in batches of 100; null any branch tip pointing into the batch
await this._db.run(`UPDATE _gristsys_ActionHistoryBranch SET actionRef = NULL
  WHERE actionRef IN (${ids})`);
```

**Flow:** Pruning triggers ONLY at shared-tip advance sites (`initialize`, `recordNextShared`, `acceptNextSharedAction`). Skip-until-period → aggregate check against limits×1.25 → if oversized, re-read branches **inside the same transaction**, walk the shared chain accumulating count/bytes, cut at the first row past a hard limit (with `count > 1` guaranteeing at least one survivor), delete tail-to-front in batches of 100, nulling branch tips that referenced deleted rows per batch. Deliberately NO `VACUUM` here (comment: 30s on a 2GB doc "obnoxious... while the user is waiting"); `deleteActions(keepN)` — the explicit trim API — DOES `requestVacuum()` after deleting everything except the newest keepN rows (`NOT IN` inverted delete, tips nulled when `NOT IN` kept ids).
**Invariant:** Only the front of the **shared** chain is ever pruned — unsent/sent local work is untouchable (working on shared "to avoid the possibility of deleting history that has not yet been shared"). At least one action always survives. Branch tips referencing deleted rows MUST be nulled in the same pass or they dangle (dangling tips would resurrect phantom ancestors in the CTE walk).
**Probe:** `test/server/lib/ActionHistory.ts` — `"can automatically prune long history"` (:449), `"can automatically prune bulky history"` (:476).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "grist-core", query: "_pruneLargeHistory ACTION_HISTORY_MAX_ROWS", limit: 5 });
```
## Verdict
Adopt the period-gated two-phase prune (cheap aggregate → transactional precise scan), grace-factor headroom, shared-only deletion, batched deletes with tip-nulling, and vacuum-deferral-to-explicit-API; adapt limits/env names/batch size; omit the specific 2GB benchmark commentary.
