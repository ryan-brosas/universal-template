<!-- capsule-v2 -->
# Chunk metadata marker courtesy — how does an internal diagnostic marker coexist with caller domain data?

**Source:** zep Apache-2.0 @ `7de18dfa`; Codebase Memory `ext-zep`. **Question:** When a chunker wants to stamp `chunk: "i/total"` into episode metadata, what happens on collision or key-budget exhaustion?

## TextChunker marker logic
**Path/Symbol:** `ingestion/src/zep_ingest/transforms/chunker.py:15` (`TextChunker`), `:40` (`apply`), `:61` (`include_chunk`); mirrored by `limits.py:55` (`include_part`). Budget: `MAX_METADATA_KEYS = 10` (types.py).
**Signature:** `TextChunker(*, chunk_size=500, overlap=50, min_chunk_size=100, data_types=frozenset({"text"}), max_document_chars=50_000)`; raises ConfigurationError if `overlap >= chunk_size`.
**Data Shape:** Emits one Episode per piece with metadata copy + optional `chunk` marker; sets internal `document` field to the source text (capped at max_document_chars) for the downstream contextualizer.

### Decisive source
```python
base_metadata = dict(episode.metadata or {})
# the marker is diagnostic and the caller's value is domain data, so a
# name collision omits the marker rather than overwriting
include_chunk = "chunk" not in base_metadata and len(base_metadata) < MAX_METADATA_KEYS
if "chunk" in base_metadata:
    self.warnings.append("Internal 'chunk' metadata marker omitted because the
        episode already carries its own 'chunk' metadata key; ...")
elif not include_chunk:
    self.warnings.append("... already has the API maximum of 10 metadata keys.")
```

**Flow:** skip episodes ≤ chunk_size → split → merge undersized tail (`<min_chunk_size`) into previous piece when combined ≤ chunk_size → unchanged single piece? yield original Episode object : fan out with per-piece metadata copies + marker.
**Invariant:** Caller domain data ALWAYS beats internal diagnostics — overwrite would corrupt user semantics; silent omission would hide degraded filterability, so each omission emits a distinct warning naming its reason. Metadata is copied per piece (never shared-mutated). The tail-merge keeps tiny orphan chunks from polluting the graph.
**Probe:** `grep -c 'def test' ingestion/tests/test_chunker.py` → ≥12; collision/limit warnings covered there and in `tests/test_limits.py::test_part_markers_count_only_kept_pieces`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-zep", query: "TextChunker chunk marker metadata collision", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt omit-with-warning marker etiquette + per-piece metadata copies + tail merge; adapt marker key names and budget to your API; omit document plumbing if you have no contextualizer.
