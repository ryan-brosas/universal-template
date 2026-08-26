<!-- capsule-v2 -->
# SQLite WAL returning batch — How does a multi-row WAL insert return seq_ids when RETURNING order is unspecified?

**Source:** Chroma Apache-2.0 `main@93652ec0869489b803fe1682427fc02bd47bec14`; Codebase Memory `ext-chroma`. **Question:** submit_embeddings must give callers seq_ids in input order, but SQLite's RETURNING clause does not guarantee row order — what is the correct pattern?

## SqlEmbeddingsQueue.submit_embeddings
**Path/Symbol:** `chromadb/db/mixins/embeddings_queue.py:submit_embeddings` (:187-270), `max_batch_size` (:321-342).
**Signature:** `submit_embeddings(collection_id, embeddings: Sequence[OperationRecord]) -> Sequence[SeqId]`; builds ONE pypika multi-row insert with 6 columns per record (operation, topic, id, vector, encoding, metadata).
**Data Shape:** `embeddings_queue(seq_id INTEGER PK AUTOINCREMENT, operation INT, topic, id, vector BLOB, encoding, metadata JSON)`; op codes ADD=0/UPDATE=1/UPSERT=2/DELETE=3; vectors are float32 `.tobytes()` blobs (`encode_vector`); notification happens INSIDE the tx.

### Decisive source
```python
with self.tx() as cur:
    sql, params = get_sql(insert, self.parameter_format())
    # The returning clause does not guarantee order, so we need to do reorder
    # the results. https://www.sqlite.org/lang_returning.html
    sql = f"{sql} RETURNING seq_id, id"  # Pypika doesn't support RETURNING
    results = cur.execute(sql, params).fetchall()
    # Reorder the results
    seq_ids = [cast(SeqId, None)] * len(results)
    ...
    for seq_id, id in results:
        seq_ids[id_to_idx[id]] = seq_id
        ...build LogRecord...
    self._notify_all(topic_name, embedding_records)
    if self.config.get_parameter("automatically_purge").value:
        self.purge_log(collection_id)
    return seq_ids
```
`max_batch_size` is derived at runtime: `PRAGMA compile_options` → parse `MAX_VARIABLE_NUMBER=<n>` → `n // VARIABLES_PER_RECORD(6)`, falling back to 999//6 for sqlite < 3.32.

**Flow:** validate batch size → persist config bootstrap → one INSERT…RETURNING → reorder via `id_to_idx` map → notify subscribers in-tx (consumer callbacks run synchronously; exceptions are LOGGED not raised to "preserve async semantics for consistency between local and distributed configurations", re-raised only under pytest via `_called_from_test`) → optional auto-purge.
**Invariant:** Callers index returned seq_ids against their INPUT order; consumer out-of-order delivery across a single call is explicitly allowed by the Producer contract docstring. Duplicate IDs inside one batch would collide in `id_to_idx` — upstream relies on API-level validation to prevent that.
**Probe:** `/tmp/chroma-p1/probe_battery.py` wal.* checks (RETURNING string, pragma parse fallback, error-swallow anchor — GREEN). Upstream: `chromadb/test/db/test_embeddings_queue.py`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-chroma", query: "SqlEmbeddingsQueue submit_embeddings RETURNING seq_id notify_all max_batch_size", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the RETURNING-reorder pattern and pragma-derived batch ceilings; adapt the storage medium (Postgres needs no reorder trick but keeps the same contract); omit the in-process notification shortcut if your consumers are cross-process (upstream's own class docstring forbids it there).
