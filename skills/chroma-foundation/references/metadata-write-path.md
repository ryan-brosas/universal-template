<!-- capsule-v2 -->
# Metadata write path — How are upserts routed without breaking the primary key, and how do typed values get stored?

**Source:** Chroma Apache-2.0 `main@93652ec0869489b803fe1682427fc02bd47bec14`; Codebase Memory `ext-chroma`. **Question:** INSERT OR REPLACE deletes-and-reinserts (changing the row id) — so how does the write path route adds vs updates, and what is the None-means-delete contract?

## SqliteMetadataSegment._insert_record / _update_metadata / _delete_record
**Path/Symbol:** `chromadb/segment/impl/metadata/sqlite.py:_insert_record` (:272-305), `_update_metadata` (:307-325), `_insert_metadata` (:327-416), `_delete_record` (:418-468).
**Signature:** `_insert_record(cur, record, upsert: bool)`; insert uses `sql + "RETURNING id"` and catches `sqlite3.IntegrityError`.
**Data Shape:** `embeddings(id INTEGER PK AUTOINCREMENT, segment_id, embedding_id, seq_id)`; `embedding_fulltext_search(rowid=id, string_value)` FTS5 table keyed BY the internal id.

### Decisive source
```python
sql = sql + "RETURNING id"
try:
    id = cur.execute(sql, params).fetchone()[0]
except sqlite3.IntegrityError:
    # Can't use INSERT OR REPLACE here because it changes the primary key.
    if upsert:
        return self._update_record(cur, record)
    else:
        logger.warning(f"Insert of existing embedding ID: ...")
        return  # async path: warn, don't raise

# _update_metadata: None value = delete that key
to_delete = [k for k, v in metadata.items() if v is None]
...
# _insert_metadata dispatch order matters:
if isinstance(value, str): ...
elif isinstance(value, bool): ...      # BEFORE int: isinstance(True,int) is True
elif isinstance(value, int): ...
elif isinstance(value, float): ...
sql = sql.replace("INSERT", "INSERT OR REPLACE")   # safe only on (id,key) child rows
```

**Flow:** ADD→INSERT…RETURNING; conflict → UPDATE if upsert else warn. UPDATE bumps seq_id then rewrites metadata. DELETE removes FTS rows via `rowid IN (subselect of ids)` FIRST, then the embeddings row, then metadata manually — the comment says cascade cannot be used because "that triggers on replace". Document writes go to `chroma:document` metadata AND the FTS table; on IntegrityError the old FTS row is deleted and re-inserted.
**Invariant:** The surrogate PK of `embeddings` must never change for a given embedding (vector-segment label maps reference it); metadata child rows MAY be replaced by (id,key). Bool-before-int ordering is mandatory.
**Probe:** `/tmp/chroma-p1/probe_battery.py` byte-exact greps on RETURNING ladder, bool-first dispatch, FTS delete-retry (`metadata-write-path` anchors all GREEN); upstream `chromadb/test/segment/impl/metadata/` suites.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-chroma", query: "_insert_record RETURNING id IntegrityError _update_metadata chroma:document", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the RETURNING-conflict-update routing and None-means-delete semantics; adapt to your DB's native upsert (Postgres ON CONFLICT) while preserving stable surrogate keys; omit the FTS5 specifics unless porting $contains.
