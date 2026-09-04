<!-- capsule-v2 -->
# WAL purge coalesce guard — How do you truncate a log when multiple segments replay it at different speeds?

**Source:** Chroma Apache-2.0 `main@93652ec0869489b803fe1682427fc02bd47bec14`; Codebase Memory `ext-chroma`. **Question:** purge_log deletes WAL entries "seen" by segments — what single mistake makes that lose unreplayed records, and how does the code prevent it?

## SqlEmbeddingsQueue.purge_log
**Path/Symbol:** `chromadb/db/mixins/embeddings_queue.py:purge_log` (:132-175).
**Signature:** `purge_log(collection_id) -> None`; retention watermark = MIN over the collection's segments of their persisted max_seq_id.
**Data Shape:** `segments(id, collection, scope, …)` LEFT JOIN `max_seq_id(segment_id, seq_id)`; missing row ⇒ segment has never flushed.

### Decisive source
```python
segment_ids_q = (
    self.querybuilder().from_(segments_t)
    # This coalesce prevents a correctness bug when > 1 segments exist and:
    # - > 1 has written to the max_seq_id table
    # - > 1 has not never written to the max_seq_id table
    # In that case, we should not delete any WAL entries as we can't be sure
    # that the all segments are caught up.
    .select(functions.Coalesce(Table("max_seq_id").seq_id, -1))
    .where(segments_t.collection == ParameterValue(self.uuid_to_db(collection_id)))
    .left_join(Table("max_seq_id"))
    .on(segments_t.id == Table("max_seq_id").segment_id)
)
...
min_seq_id = min(row[0] for row in results)
q = (... .where(t.seq_id < ParameterValue(min_seq_id))
         .where(t.topic == ParameterValue(topic_name)) .delete())
```

**Flow:** gather per-segment watermarks (COALESCE→−1 for never-flushed segments, which pins min to −1 and deletes NOTHING) → delete only strictly-below-watermark rows of this topic → run after every submit when `automatically_purge` is on (default ON only for fresh systems — config bootstrap checks `_get_wal_size()==0`, so upgrades never silently flip retention on).
**Invariant:** A record may be deleted only if EVERY segment's durable progress exceeds it; one laggard segment must freeze retention for the whole collection. delete_log (drop whole topic) is reserved for collection deletion.
**Probe:** `/tmp/chroma-p1/probe_battery.py` `wal.coalesce` byte-exact grep (GREEN); upstream behavior pinned by `chromadb/test/db/test_embeddings_queue.py` purge cases.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-chroma", query: "purge_log Coalesce max_seq_id min_seq_id embeddings_queue", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the min-across-consumers watermark rule for any log-replay storage (this is Chroma's WAL/compaction-cursor equivalent at embedded scale); adapt to per-shard cursors in distributed systems (the distributed Rust worker generalizes exactly this into compaction cursors); omit topic naming specifics.
