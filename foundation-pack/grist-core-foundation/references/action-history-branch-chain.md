<!-- capsule-v2 -->
# Action-history branch chain — how does a linear action log track shared/sent/unsent subhistories without losing ancestry?

**Source:** grist-core (Apache-2.0), `main@b83224bbe9c88910dfeb28922df254a26f702f68`; Codebase Memory `grist-core`. **Question:** How do you persist a collaborative action history so another replica can accept exactly the actions it expects, while local work stays separable?

## ActionHistoryImpl branch chain
**Path/Symbol:** `app/server/lib/ActionHistoryImpl.ts:class ActionHistoryImpl` (177-720), `computeActionHash` (81-91), `_fetchParts` (578-606), `_addAction` (504-526).
**Signature:** `recordNextLocalUnsent(action: LocalActionBundle): Promise<void>` / `markAsSent(actions): Promise<void>` / `acceptNextSharedAction(actionHash: string | null): Promise<boolean>` / `private _fetchParts(start, end, selection, limit?, desc?): Promise<ResultRow[]>`.
**Data Shape:** Two SQLite tables. `_gristsys_ActionHistory(id=rowid, actionHash, parentRef, actionNum, body BLOB)` — `parentRef` is the **SQLite rowid of the parent action**, forming a physical linked list. `_gristsys_ActionHistoryBranch(name, actionRef)` holds three tips: `shared` ⊆ `local_sent` ⊆ `local_unsent`. Body blobs are Grist-marshalled bundles whose embedded `actionNum`/`actionHash` are RESET from the row on decode (`decodeActionFromRow`, 67-73) — the row columns win over the blob.

### Decisive source
```ts
// _fetchParts: ancestry walk, not ORDER BY id
const rows = await this._db.all(`WITH RECURSIVE
    actions(id) AS (
      VALUES(?)
      UNION ALL
        SELECT parentRef FROM _gristsys_ActionHistory, actions
          WHERE _gristsys_ActionHistory.id = actions.id
            AND parentRef IS NOT NULL
            AND _gristsys_ActionHistory.id IS NOT ?)
  SELECT ${selection} from actions
    JOIN _gristsys_ActionHistory ON actions.id = _gristsys_ActionHistory.id
    WHERE _gristsys_ActionHistory.id IS NOT ?
    ORDER BY actionNum ${desc ? "DESC " : ""} ${limit ? ("LIMIT " + limit) : ""}`,
  end.actionRef, start ? start.actionRef : null, start ? start.actionRef : null);

// _addAction: insert + tip move must be one transaction
return this._db.execTransaction(async () => {
  const id = await this._db.runAndGetId(`INSERT INTO _gristsys_ActionHistory
    (actionHash, parentRef, actionNum, body) VALUES (?, ?, ?, ?)`,
    action.actionHash, branch.actionRef, action.actionNum, buf);
  await this._db.run(`UPDATE _gristsys_ActionHistoryBranch SET actionRef = ?
    WHERE name = ?`, id, branch.branchName);
  return id;
});
```

**Flow:** Every append writes the row with `parentRef = current branch tip`, then moves that branch tip, atomically. Ranges (`fetchAllLocalUnsent` = local_sent→local_unsent, `fetchAllLocal` = shared→local_unsent, `getRecentStates`) are computed by walking `parentRef` backwards from `end` until `start` (excluded) via the recursive CTE, then ordering by `actionNum`. Sharing is a two-step handshake: producer calls `markAsSent(actions)` which verifies each candidate's `actionHash` **in order** against the sent→unsent window (`"markAsSent() got an unexpected action"` on mismatch) and advances the `local_sent` tip in a `finally`; consumer calls `acceptNextSharedAction(expectedHash?)` which checks the first candidate in the shared→sent window and advances the `shared` tip. `computeActionHash` = sha256-hex over marshal(actionNum, parentActionHash, info, stored) — each hash commits to its parent, chaining the whole history. `recordNextShared`/`skipActionNum` demand all three tips be identical (`"...not defined when branches not in sync"`). `initialize()` restores counters from tip rows (+1) and derives `haveLocalSent/haveLocalUnsent` by comparing tip `actionNum`s.
**Invariant:** Ancestry lives in `parentRef` links, never in rowid order — a port that sorts by `id` instead of walking the chain corrupts history the moment branches diverge. Row insert and tip move must share one transaction, or a crash strands a dangling tip. A branch tip pointing at a deleted row must be nulled (see history-prune-ladder).
**Probe:** `test/server/lib/ActionHistory.ts` — `"check path to acceptance"` (:270, full shared/sent/unsent progression), `"check reject disordered"` (:293), `"markAsSent checks sanity"` (:304), `"can persist actionNum across restarts"` (:416).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "grist-core", query: "ActionHistoryImpl acceptNextSharedAction markAsSent", limit: 10 });
```
## Verdict
Adopt the three-tip branch table + parentRef chain + ordered-hash handshake for any replicated action/edit log; adapt table names and the marshaller; omit Grist's LocalActionBundle field specifics. Note: parent-action deletion does NOT rewrite children's stored `parentActionHash` (TODO at 171-174) — treat links as append-only.
