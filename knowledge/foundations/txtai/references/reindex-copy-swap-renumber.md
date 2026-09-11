<!-- capsule-v2 -->
# Reindex copy-swap renumbering — how a content store survives deletes without corrupting positional ids

**Source:** txtai Apache-2.0 `master@a10667a1c2a4721ce719f3648bd1aeedd03dd84a` (9.13.0); Codebase Memory `txtai`. **Question:** How can indexids be renumbered densely while streaming every surviving row out for vector re-embedding?

## Connected graph-selected seam
**Path/Symbol:** `src/python/txtai/database/rdbms.py:RDBMS.reindex` (:78-109), `.reindexstart/reindexend` (:417-442); SQL `schema/statement.py:COPY_SECTIONS/STREAM_SECTIONS` (:75-85); consumer `embeddings/base.py:Embeddings.reindex` (:260-290).
**Signature:** `reindex(config) -> generator of (uid, text|object, tags)`; consumer `index(function(self.database.reindex(config)), True)`.
**Data Shape:** working table `rebuild` mirrors sections DDL; stream rows `(s.id, s.text, data, object, s.tags)`.

### Decisive source
```python
COPY_SECTIONS = (
    "INSERT INTO %s SELECT (select count(*) - 1 from sections s1 where s.indexid >= s1.indexid) indexid, "
    + "s.id, %s AS text, s.tags, s.entry FROM sections s LEFT JOIN documents d ON s.id = d.id ORDER BY indexid"
)
```
```python
for uid, text, data, obj, tags in self.rows():
    if not text and self.encoder and obj:
        yield (uid, self.encoder.decode(obj), tags)
    else:
        data = json.loads(data) if data and isinstance(data, str) else data
        yield (uid, data if data else text, tags)
```

**Flow:** configure(new config) → resolve text column → create `rebuild` table → COPY_SECTIONS inserts survivors with NEW dense indexids computed by a correlated count of preceding rows → STREAM_SECTIONS streams each row joined to documents+objects, decoding objects through the encoder and JSON `data` columns (data preferred over raw text when present) → DROP sections → RENAME rebuild→sections → recreate the id index. Consumer merges config, force-preserves `content` and `objects` keys, and feeds the generator straight into index().

**Invariant:** The correlated-subquery renumbering is O(n²) in SQLite but keeps ordering deterministic and gap-free — a port that instead reuses old indexids leaves delete gaps that misalign every positional ANN structure rebuilt from this stream. Objects decode BEFORE yielding so the new index embeds real content, not pickled bytes. Graph caveat: trace_path shows ZERO static callers of RDBMS.reindex — dispatch is dynamic (`self.database.reindex`), so graph-based blast-radius tools miss this edge.

**Probe:** `test/python/testdatabase/testrdbms.py:testReindex` (:599-616 delete ids 0,1 then reindex then search), `test/python/testdatabase/testencoder.py:testReindex/testReindexFunction` (:125-171 objects survive reindex, incl. streaming function).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "txtai", query: "reindex rebuild sections copy swap rename", limit: 10, fields: ["signature", "name", "file"] });
```
Executed live at pin: top hits `Database.reindex` (:64-73) / `RDBMS.reindex` (:78-109) / `Embeddings.reindex` (:260-290) line-exact.

## Verdict
Adopt copy-swap with dense correlated-count renumbering + decode-on-stream; adapt to batched window functions for large stores (the count subquery is quadratic); omit JSON-data preference only if you never store structured documents. Coverage caveat: dynamic-dispatch edge invisible to static call graphs. Cited paths no_recorded_issue @ gen 2026-08-25T20:20:01Z.
