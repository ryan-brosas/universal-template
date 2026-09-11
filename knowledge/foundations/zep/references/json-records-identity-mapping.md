<!-- capsule-v2 -->
# JSON records loader identity mapping — how do structured records become unified-entity json episodes?

**Source:** zep Apache-2.0 @ `7de18dfa`; Codebase Memory `ext-zep`. **Question:** How are id/name/description lifted from caller-named fields without key-clobbering, and what metadata may be promoted?

## JsonRecordsLoader
**Path/Symbol:** `ingestion/src/zep_ingest/loaders/json_records.py:29` (`_RESERVED_METADATA_KEYS = ("source_type","file_name")`), `:30` (`MAX_METADATA_FIELDS = MAX_METADATA_KEYS - 2`), `:33` (`_parse_timestamp`), `:52` (`_find_non_finite`), `:74` (`JsonRecordsLoader`), `:148` (`_read`), `:174` (`_to_episode`).
**Signature:** format auto-detects by suffix (.jsonl/.csv/else json); a .json file failing full parse falls back to JSONL lines ONLY in auto mode (explicit format="json" re-raises).
**Data Shape:** One episode per record, data_type="json", body = `json.dumps(record, allow_nan=False)`; provenance keys source_type/file_name stamped on every episode and NEVER liftable.

### Decisive source
```python
# every field the caller names is read from the record AS THEY WROTE IT,
# never from a key the loader just wrote: with id_field='sku' and
# name_field='id' the name is still the record's own 'id'.
original = record
record = dict(record)
for target, field in (("id", self.id_field), ("name", self.name_field),
                      ("description", self.description_field)):
    if field and field in original:
        record[target] = original[field]
...
# metadata_fields promotes keys of the episode as emitted, so a lifted value
# always matches the episode body under that key — a mapped identity key or
# an injected record_type included.
for f in self._liftable_fields:
    if f in record and is_scalar_or_scalar_array(record[f]):
        metadata[f] = record[f]
```

**Flow:** constructor rejects over-budget metadata_fields BEFORE any file read ("an over-budget request otherwise survives preview() and aborts run()") → per-record `_find_non_finite` walks dicts/lists building dotted paths ('dims.w', 'sizes[0].w') and RAISES naming record+path — NaN/Infinity would render the body unparseable and send null via metadata → created_at parsed only from the ORIGINAL field; missing counts warned per file.
**Invariant:** Reserved provenance keys can never be overwritten by record content ("what the episode reports about its own origin stays trustworthy"); collisions warn once per pass (property of metadata_fields, not records). Non-finite refusal happens at the record — "the one point every format reaches".
**Probe:** `grep -c 'def test' ingestion/tests/test_json_records_loader.py` → 37.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-zep", query: "JsonRecordsLoader id_field name_field metadata non-finite", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt original-record field reads + reserved provenance + path-naming non-finite rejection; adapt identity fields to your schema; omit CSV if your rows carry nested fields.
