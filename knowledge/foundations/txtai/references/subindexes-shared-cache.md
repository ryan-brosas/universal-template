<!-- capsule-v2 -->
# Subindexes (Indexes) — parallel named index spaces sharing one documents stream and model cache

**Source:** txtai Apache-2.0 `main@a10667a` (9.13.0); Codebase Memory `ext-txtai`. **Question:** How do multiple named indexes under one Embeddings instance receive documents, resolve ids, and route searches?

## Connected graph-selected seam
**Path/Symbol:** `src/python/txtai/embeddings/index/indexes.py:Indexes.insert` (:102-130), `.index/.upsert` (:143-166), `.findmodel` (:87-100), `.load` (:168-180); creation `embeddings/base.py:createindexes` (:1031-1053); search routing `search/base.py:subindex` (:128-148).
**Signature:** `insert(documents, index=None, checkpoint=None)`; subindex search: `self.indexes[index].batchsearch(queries, limit, weights)` then `resolve`.
**Data Shape:** config `indexes: {name: config}` → dict of full Embeddings instances sharing ONE `models` cache; Documents buffer holds `(indexid, document, None)` batches.

### Decisive source
```python
# insert — renumber docs into the SUBINDEX id space
batch = []
for _, document, _ in documents:
    parent = document
    if isinstance(parent, dict):
        parent = parent.get(self.text, document.get(self.object))

    # Add if field is available or top-level indexing is disabled
    if parent is not None or not self.indexing:
        batch.append((index, document, None))
        index += 1
self.documents.add(batch)
```
```python
# load — subindexes aren't required to have data
for name, index in self.indexes.items():
    directory = os.path.join(path, name)
    if index.exists(directory):
        index.load(directory)
```

**Flow:** each subindex is a complete Embeddings built with a SHARED models cache (one model load for N indexes) → Transform.load fans every batch into Indexes.insert → docs carrying text/object (or all when top-level indexing disabled) are RENUMBERED into a fresh per-subindex id space starting at the passed offset → index()/upsert() drain the buffer into each subindex (checkpoint namespaced `{checkpoint}/{name}`) → searches name a subindex explicitly (`index=`) else default() picks the FIRST registered when no top-level ann/scoring exists.

**Invariant:** Subindex ids are INDEPENDENT of parent ids — results pass through `Search.resolve` which maps back via parent ids only when content is disabled; assuming shared id spaces corrupts cross-index joins. Model cache sharing means closing one subindex's model closes it for all (models dict is passed by reference).

**Probe:** `test/python/testembeddings.py:testSubindex` (:548-596), `testShortcuts` combos (:473-495).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-txtai", query: "Indexes subindex insert findmodel default", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt shared-model-cache construction + per-subindex renumbering + optional-directory loads + first-index defaulting; adapt id mapping strategy; omit if single-index.
