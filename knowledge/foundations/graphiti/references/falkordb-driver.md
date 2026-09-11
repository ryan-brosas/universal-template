<!-- capsule-v2 -->
# Falkor driver — datetime coercion, result transpose, index-idempotence, close-drain

**Source:** graphiti MIT `main@401c59a6`; Codebase Memory `graphiti`. **Question:** what invariants does the FalkorDB driver maintain that a porter would get wrong (datetime encoding, result shape, index idempotence, teardown ordering)?

## Connected graph-selected seam
**Path/Symbol:** `graphiti_core/driver/falkordb_driver.py:FalkorDriver` (:127–375); `execute_query` (:238–273), `convert_datetimes_to_strings` (:330–350), `_strip_nul_bytes` (:78–88), `delete_all_indexes` (:298–330), `close` (:286–297), `clone` (:335–363), `_get_graph` (:226–231).
**Signature:** `async execute_query(cypher_query_, **kwargs) -> (records: list[dict], header: list[str], None)`; `clone(database: str) -> GraphDriver`.
**Data Shape:** returns a 3-tuple `(records, header, None)` where `records` is a list of dicts (row → `{field_name: value}`), `header` is the list of field names, and the third element is always `None` (a placeholder for dialects that return a third value). Datetime params are coerced to ISO strings before the query; NUL bytes are stripped from params.

### Decisive source
```python
async def execute_query(self, cypher_query_, **kwargs):
    graph = self._get_graph(self._database)
    params = convert_datetimes_to_strings(dict(kwargs))
    params = _strip_nul_bytes(params)
    try:
        result = await graph.query(cypher_query_, params)
    except Exception as e:
        if 'already indexed' in str(e):
            logger.info(f'Index already exists: {e}')
            return None          # index creation is idempotent
        logger.error(...); raise
    header = [h[1] for h in result.header]
    records = []
    for row in result.result_set:
        record = {}
        for i, field_name in enumerate(header):
            record[field_name] = row[i] if i < len(row) else None
        records.append(record)
    return records, header, None
```

**Flow:** `execute_query` coerces datetimes to ISO strings (FalkorDB has no datetime type), strips NUL bytes, runs the query, swallows `'already indexed'` as idempotent index creation, and transposes FalkorDB's `result_set` (list-of-lists) into a list-of-dicts keyed by header. `delete_all_indexes` enumerates `CALL db.indexes()`, dispatches `DROP INDEX` vs `DROP FULLTEXT INDEX` by index type and entity type (NODE vs RELATIONSHIP), and fans out drops with `asyncio.gather`. `close` cancels the init task (draining its exception), then closes the client via an `aclose`/`connection.aclose`/`connection.close` fallback ladder. `clone` returns `self` when the database matches, a fresh driver on the default group, or a new driver with the same connection otherwise.
**Invariant:** (1) datetime params MUST be converted to ISO strings before any query — passing a `datetime` object breaks FalkorDB; (2) the result is ALWAYS `(records, header, None)` — a porter reading only `records` loses the header, and the third `None` slot is part of the contract; (3) index creation is idempotent via the `'already indexed'` swallow — do not treat it as a failure; (4) `close` must drain the init task (observe its exception) before closing the connection, else a pending task's exception goes unobserved.
**Probe:** `tests/driver/test_falkordb_driver.py` (pins `execute_query` result shape, datetime coercion, and index behavior).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "graphiti", query: "FalkorDriver execute_query convert_datetimes_to_strings delete_all_indexes _strip_nul_bytes", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the datetime→ISO coercion, the `(records, header, None)` result contract, and the idempotent-index swallow verbatim (all three are easy to get wrong); adapt the index-drop SQL to your dialect; omit the `_strip_nul_bytes` pass if your store tolerates NUL bytes. Complements `driver.md` (the ABC) by pinning the concrete Falkor execution/teardown invariants.
