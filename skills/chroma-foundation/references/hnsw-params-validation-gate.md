<!-- capsule-v2 -->
# HNSW params validation gate — Where is the boundary between accepting and validating hnsw:* collection metadata?

**Source:** Chroma Apache-2.0 `main@93652ec0869489b803fe1682427fc02bd47bec14`; Codebase Memory `ext-chroma`. **Question:** Which code path rejects unknown/bad `hnsw:` keys, when does it run, and what are the defaults a port must reproduce?

## HnswParams / PersistentHnswParams
**Path/Symbol:** `chromadb/segment/impl/vector/hnsw_params.py:Params._select/_validate` (:26-43), `HnswParams.__init__/extract` (:46-70), `PersistentHnswParams` (:73-88).
**Signature:** `extract(metadata) -> Metadata` = select keys with prefix `hnsw:` THEN validate against the operator table; constructors read defaults via `metadata.get(key, default)` WITHOUT validation.
**Data Shape:** Defaults — space=l2, construction_ef=100, search_ef=100, M=16, num_threads=cpu_count, resize_factor=1.2; persistent adds batch_size=100 (>2 required), sync_threshold=1000 (>2 required).

### Decisive source
```python
param_validators: Dict[str, Validator] = {
    "hnsw:space": lambda p: bool(re.match(r"^(l2|cosine|ip)$", str(p))),
    "hnsw:construction_ef": lambda p: isinstance(p, int),
    ...
}
persistent_param_validators = {
    "hnsw:batch_size": lambda p: isinstance(p, int) and p > 2,
    "hnsw:sync_threshold": lambda p: isinstance(p, int) and p > 2,
}

@staticmethod
def extract(metadata):
    segment_metadata = HnswParams._select(metadata)
    HnswParams._validate(segment_metadata, param_validators)
    return segment_metadata
```

**Flow (live-verified):** create-collection time → `LocalSegmentManager._segment()` calls the segment class's `propagate_collection_metadata`, which runs `extract()` → ValueError on unknown key or bad value (e.g. space not in l2|cosine|ip) BEFORE any segment persists. Constructor-time reads (`PersistentHnswParams({"hnsw:bogus":1})`) do NOT raise — validation lives in extract only. The selected subset is stored as SEGMENT metadata, so the manager can rebuild segments later without the collection row.
**Invariant:** Unknown-parameter rejection must happen at propagation, not at index init; validators double as documentation of the accepted knob set. `str(p)` on space means numeric spaces coerce-and-fail rather than crash.
**Probe:** `/tmp/chroma-p1/probe_battery.py` params.* live checks — defaults asserted, unknown-key constructor acceptance confirmed live, bad-space extract raises (GREEN). Upstream: `chromadb/test/segment/impl/vector/` param tests.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-chroma", query: "HnswParams PersistentHnswParams param_validators propagate_collection_metadata", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt validate-at-propagation with default-at-construction split; adapt the knob set to your engine's tunables; omit multiprocessing.cpu_count() as thread default (containers lie — use your own cgroup-aware value).
