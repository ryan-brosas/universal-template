<!-- capsule-v2 -->
# Cross-repo pattern: append-only snapshot ledger with newest-row read — crewAI flow persistence and checkpoint lineage as one contract

**Source:** crewAI MIT `main@9e9a8577becc322f98a966ad88d7904251049744` (`flow/persistence/sqlite.py:157–198` + `state/provider/json_provider.py:113–123`); Codebase Memory `ext-crewAI`. **Question:** What do the SQLite state store and the JSON checkpoint store share that makes "latest wins" trustworthy under concurrency?

## Pattern: never update in place; order by a monotonic key
**Path/Symbol:** sqlite `save_state` INSERT + `load_state` `ORDER BY id DESC LIMIT 1`; json_provider `_build_path` timestamp+uuid filenames + `_chain_lineage` parent chaining (`state/runtime.py:216–227`).
**Signature:** `save_state(flow_uuid, method_name, state_data)` ↔ `checkpoint(data, location, *, parent_id, branch)`.
**Data Shape:** rows keyed `(autoincrement id, flow_uuid, ...)`; files named `{ts}_{uuid8}_p-{parent}.json` — both embed a per-write monotonic/unique token.

### Decisive source
```python
# sqlite: every completion is an INSERT — history IS the table
conn.execute("""INSERT INTO flow_states (
    flow_uuid, method_name, timestamp, state_json) VALUES (?, ?, ?, ?)""", ...)
...
SELECT state_json FROM flow_states
WHERE flow_uuid = ?
ORDER BY id DESC
LIMIT 1
```
```python
# json provider: same idea in filenames — parent encoded, id = stem prefix
filename = f"{ts}_{short_uuid}_p-{parent_suffix}.json"
idx = stem.find("_p-")
return stem[:idx] if idx != -1 else stem
```

**Flow:** write path always APPENDS (new row / new file) carrying a fresh unique+ordered token → read path selects the single newest entry for the key → lineage (sqlite: implicit via row order; json: explicit `_p-` parent chain) is derivable without mutating anything.
**Invariant:** No UPDATE-in-place anywhere: torn writes leave older intact versions readable. The ordering token must be monotonic (autoincrement id / UTC-timestamped name) or "latest" becomes ambiguous. Reads take no locks (WAL readers / immutable files) while writes serialize through the realpath-named lock or unique filenames.
**Probe:** `.venv/bin/python -m pytest lib/crewai/tests/test_flow_persistence.py -q` (expect 15 passed incl. latest-row restoration across multiple saves); static anchors: `ORDER BY id DESC` ×1 :193, `INSERT INTO flow_states` ×2 (:117/:210).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-crewAI", query: "append insert flow states order desc latest filename lineage", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt append-plus-monotonic-token for any durable snapshot need; adapt tokens to your storage's native ordering; omit explicit parent chains when implicit recency suffices.
