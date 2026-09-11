<!-- capsule-v2 -->
# invocation blob externalization — when do invocation payloads move out of the row into blob storage?

**Source:** ell MIT `main@9d129846203e75efeb4e5cddd3fb1c164dc0b243`; Codebase Memory `ext-ell`. **Question:** How do I keep a relational invocation log fast when some invocations carry megabytes of prompt/output?

## size-gated gzip blob swap
**Path/Symbol:** `src/ell/stores/models/core.py:InvocationContentsBase.should_externalize` (:151-170); writer side `src/ell/lmp/_track.py:_write_invocation` (:274-310); blob layout `src/ell/stores/sql.py:SQLBlobStore` (:480-506).
**Signature:** `should_externalize(self) -> bool` (cached_property); `store_blob(blob: bytes, blob_id: str) -> str`.
**Data Shape:** threshold `total_size > 102400` bytes ("Precisely 100kb in bytes", in-source comment); externalized rows keep ONLY `(invocation_id, is_external=True)`.

### Decisive source
```python
# _track.py:283-296
if invocation_contents.should_externalize and config.store.has_blob_storage:
    invocation_contents.is_external = True

    # Write to the blob store
    blob_id = config.store.blob_store.store_blob(
        json.dumps(
            invocation_contents.model_dump(), default=str, ensure_ascii=False
        ).encode("utf-8"),
        invocation_id,
    )
    invocation_contents = InvocationContents(
        invocation_id=invocation_id,
        is_external=True,
    )
```

```python
# sql.py:496-505 — fan-out path so one dir never holds millions of blobs
def _get_blob_path(self, id: str, depth: int = 2) -> str:
    assert "-" in id, "Blob id must have a single - in it to split on."
    _type, _id = id.split("-")
    increment = 2
    dirs = [_type] + [
        _id[i : i + increment] for i in range(0, depth * increment, increment)
    ]
```

**Flow:** five JSON fields (params, results, invocation_api_params, global_vars, free_vars) are individually measured; over-threshold AND blob-store-configured ⇒ full dump serialized once into a gzipped file under `<type>/<2-char>/<2-char>/...`, then the row's contents object is REPLACED with the two-field stub. If contents are huge but no blob store exists, they stay inline (graceful degradation, not data loss).
**Invariant:** the stub must preserve `(invocation_id, is_external)` or readers cannot find the blob; blob ids MUST contain exactly one dash (the type/id split) — which ell ids like `invocation-<hex>` satisfy by construction. Studio serves blobs back through `/api/blob/{blob_id}` with FileNotFoundError→404.
**Probe:** deterministic anchors from repo root: `grep -n 'should_externalize' src/ell/stores/models/core.py src/ell/lmp/_track.py` → definition :152 + consumption :283; `grep -n 'has_blob_storage' src/ell/stores/store.py src/ell/lmp/_track.py` → property :31 + gate :283. No direct unit test at pin for the 100KB branch (coverage caveat recorded honestly).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ell", query: "should_externalize blob", limit: 5, fields: ["signature", "name", "file"] });
// rank-1: ext-ell.src.ell.stores.models.core.InvocationContentsBase.should_externalize @ src/ell/stores/models/core.py:152-170
```

## Verdict
Adopt measure-then-swap externalization with a type-prefixed sharded blob path. Adapt the threshold and shard depth to your expected volume. Omit nothing from the stub contract — it is what makes externalization invisible to read paths that check `is_external` before touching JSON columns.
