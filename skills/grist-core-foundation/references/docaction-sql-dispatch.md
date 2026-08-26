<!-- capsule-v2 -->
# Action→SQL dispatcher — how do document-level mutations become safe SQL on a live embedded DB while a cached schema stays coherent?

**Source:** grist-core Apache-2.0 `main@b83224bbe9c88910dfeb28922df254a26f702f68`; Codebase Memory `grist-core`. **Question:** How do you turn a stream of typed document actions (AddTable, BulkAddRecord, RenameColumn…) into parameterized SQL, and when must the in-memory type map be refreshed so subsequent writes encode correctly?

## Name-based handler dispatch + conditional metadata refresh
**Path/Symbol:** `app/server/lib/DocStorage.ts:applyStoredActions` (:1031–1057), `applyStoredAction` (:1061–1078), `_process_<ActionType>` family (:1087–1356), `_compressStoredActions` (:1928–1944), `_considerWithoutManualSort` (:1948–1957).
**Signature:** `async applyStoredAction(action: DocAction): Promise<void>` — `action[0]` is the type string, handler resolved as `(this as any)["_" + actionType]`.
**Data Shape:** `docActions: DocAction[]` = tuples `[type, tableId, ...args]`; `_docSchema: {tableId: {colId: gristType}}` loaded from `_grist_Tables`/`_grist_Tables_column` plus static schema.

### Decisive source
```ts
public async applyStoredAction(action: DocAction): Promise<void> {
  const actionType = action[0];
  const f = (this as any)["_process_" + actionType];
  if (!_.isFunction(f)) {
    log.error("Unknown action: " + actionType);        // log-and-continue, not throw
  } else {
    await f.apply(this, action.slice(1));
    const tableId = action[1];   // first arg is always tableId
    if (DocStorage._isMetadataTable(tableId) && actionType !== "AddTable") {
      await this._updateMetadata();   // type map must track schema edits
    }
  }
}
```

**Flow:** compress leading `AddRecord` + same-row `UpdateRecord*` run into one merged action (extra constraints on gristified SQLite files make split inserts differ) → dispatch by method-name convention → per-handler SQL with `quoteIdent` everywhere → on failure matching `/no column named manualSort/`, strip `manualSort` from a cloned action and retry once (tolerates "gristified" foreign SQLite tables) → metadata-table actions (except AddTable, which adds no columns yet) re-query `_grist_Tables_column` to refresh `_docSchema`.
**Invariant:** Every user table gets `id INTEGER PRIMARY KEY` so `id` aliases SQLite's rowid (row identity IS physical rowid — porters who add surrogate keys break getNextRowId and ReplaceTableData); empty bulk ops no-op early; BulkRemoveRecord chunks deletes at a fixed 10 placeholders through ONE prepared statement (not the 500-variable max); RenameTable between names differing only by case must hop through a `_tmp_` name because SQLite refuses same-case-insensitive renames in one step; unknown action types log errors instead of throwing (forward compatibility).
**Probe:** `test/server/lib/DocStorage.js` — `.AddTable` `"Should error if creating a duplicate table"` (:279), `.BulkAddRecord` (:321), `.RenameDoc` `"Should allow renaming to a name that differs only in capitalization"` (:782), `.DeleteActions` (:803/:880). Whole-file harness builds a fresh doc per test via `createFile()` + peopleSql fixture.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "grist-core",
  query: "applyStoredAction _process_BulkAddRecord _compressStoredActions manualSort", limit: 10,
  fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the name-convention dispatcher + "refresh derived caches only after actions that can invalidate them" rule — it keeps a hot write path free of unconditional re-reads. Adapt action vocabulary and chunk sizes to host; keep the id-is-rowid aliasing invariant if you want free row identity. Omit the manualSort retry unless you support importing arbitrary foreign tables into the document store.
