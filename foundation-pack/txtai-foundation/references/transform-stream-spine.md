<!-- capsule-v2 -->
# Transform/Stream document spine — the one-pass stream that feeds every datastore and the vectorizer

**Source:** txtai Apache-2.0 `main@a10667a` (9.13.0); Codebase Memory `ext-txtai`. **Question:** How must one documents iterable simultaneously build database rows, scoring, subindexes, graph AND vector batches — and how do upsert deletes stay once-per-action?

## Connected graph-selected seam
**Path/Symbol:** `src/python/txtai/embeddings/index/transform.py:Transform.stream` (:123-168), `.load` (:170-208), `.ids` (:102-121); `embeddings/index/stream.py:Stream.__call__` (:37-67); action enum `index/action.py`.
**Signature:** `Transform(embeddings, Action.INDEX|UPSERT|REINDEX, checkpoint)(documents, buffer)` → `(ids, dimensions, embeddings)`.
**Data Shape:** canonical tuple `(id, data, tags)`; batch size `config["batch", 1024]`; upsert offset seeds from `config["offset"]`.

### Decisive source
```python
# stream(): yield-for-vectorize vs batch-for-datastore split
if isinstance(document[1], dict):
    # Set text field to uid when top-level indexing is disabled and text empty
    if not self.indexing and not document[1].get(self.text):
        document[1][self.text] = str(document[0])

    if self.text in document[1]:
        yield (document[0], document[1][self.text], document[2])
        offset += 1
    elif self.object in document[1]:
        yield (document[0], document[1][self.object], document[2])
        offset += 1
else:
    yield document
    offset += 1

batch.append(document)
if len(batch) == self.batch:
    self.load(batch, offset)
    batch, offset = [], 0
```
```python
# load(): delete-once-per-action guard for UPSERT
if self.action == Action.UPSERT:
    deletes = [uid for uid, _, _ in batch if uid not in self.deletes]
    if deletes:
        self.delete(deletes)
        self.deletes.update(deletes)
```

**Flow:** Stream normalizes dicts/tuples/raw data into tuples and assigns AutoId (int sequence reset per index; uuid/uuid3/uuid5 via config `autoid`, deterministic variants hash the data; final sequence persisted back to `config["autoid"]`) → Transform yields only vectorizable docs (dicts must carry text or object column; non-dicts always yield) while accumulating EVERY doc into datastore batches → per batch: upsert-delete first, then database.insert (skipped on REINDEX), scoring.insert, indexes.insert, graph.insert → offset advances by YIELDED count (vectorized rows), which is what keeps ann rowids aligned with scoring/database indexids.

**Invariant:** offset counts yielded (vectorized) documents, not all documents — a porter that increments on every doc desyncs positional ANN ids from content rows. The `deletes` set makes duplicate uids across a single upsert safe. REINDEX skips database insert because reindex re-reads FROM the database.

**Probe:** `test/python/testembeddings.py:testUpsert` (:627-651), `testAutoId` (:51-69 int sequence + uuid modes), `testColumns` (:70-82 custom text/object columns), `testSubindex` (:548-596 subindex id spaces).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-txtai", query: "Transform stream load batch offset upsert delete", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt single-stream fan-out + yielded-count offset + delete-once set + autoid persistence; adapt batching; omit graph/subindex hooks you don't carry.
