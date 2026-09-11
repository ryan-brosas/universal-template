<!-- capsule-v2 -->
# Proxy index-change intent buffering — how are payload-index schema changes journaled on a segment that builds nothing?

**Source:** Qdrant Apache-2.0 `master@74f3e85b`; Codebase Memory `qdrant`. **Question:** When a client creates or drops a payload index while the segment is proxied, where does the change live until the wrapped segment is writable again?

## Version-gated per-field intents; nothing is built in the proxy
**Path/Symbol:** `lib/shard/src/proxy_segment/segment_entry.rs`: `delete_field_index` (:1009-1021), `delete_field_index_if_incompatible` (:1023-1041), `build_field_index` (:1043-1058), `apply_field_index` (:1060-1078); buffer type `lib/shard/src/proxy_segment/mod.rs`: `ProxyIndexChanges` (:386-430), `ProxyIndexChange` enum (:434-447).
**Signature:** `fn apply_field_index(&mut self, op_num: SeqNumberType, key: PayloadKeyType, field_schema: PayloadFieldSchema, _field_index: Vec<FieldIndex>) -> OperationResult<bool>`; buffer insert `(&mut self, key: PayloadKeyType, change: ProxyIndexChange)`.
**Data Shape:** `changed_indexes: AHashMap<PayloadKeyType, ProxyIndexChange>` with `ProxyIndexChange::{Create(schema, version), Delete(version), DeleteIfIncompatible(version, schema)}`; iteration helpers `iter_ordered` (sorted by version) / `iter_unordered`.

### Decisive source
```rust
// :1050-1057 — build is a no-op that reports success:
if self.version() > op_num {
    return Ok(BuildFieldIndexResult::SkippedByVersion);
}
Ok(BuildFieldIndexResult::Built {
    indexes: vec![], // No actual index is built in proxy segment, they will be created later
    schema: field_type.clone(),
})
// :1067-1075 — apply records an intent instead of mutating storage:
if self.version() > op_num { return Ok(false); }        // stale op ⇒ silently skipped
self.version = cmp::max(self.version, op_num);          // wrapper version advances anyway
self.changed_indexes.insert(key, ProxyIndexChange::Create(field_schema, op_num));
```

**Flow:** schema op arrives → version gate (`self.version() > op_num` ⇒ skip) → bump wrapper version → overwrite any prior intent for the same key (last-writer-wins per field) → at drain time `propagate_to_wrapped` replays intents via `iter_ordered` because "an intent with a stale version will be silently rejected by the target segment". `replicate_field_indexes` (:152-192) separately diffs indexed fields between a write segment and the wrapped segment and reconciles both directions for fresh write segments.
**Invariant:** (1) the proxy never constructs index structures — `Built { indexes: vec![] }`; (2) one intent per field name: a create after a delete replaces it, so ordering within a single key collapses to the newest intent; (3) replay must be in version order or the target's own gating drops legitimate changes.
**Probe:** direct test `lib/shard/src/proxy_segment/tests.rs::test_sync_indexes` (:423-490): keyword index on `color` replicated onto an empty write segment; then geo `location` add + `color` drop re-replicated — replica ends with `location`, without `color`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "qdrant", query: "ProxyIndexChanges insert iter_ordered replicate field indexes write segment", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt journaling schema mutations as per-key versioned intents with last-writer-wins collapse and ordered replay. Adapt the "silently skipped when stale" gate to your error policy. Omit qdrant's disposable HardwareCounterCell accounting on internal replays if you have no cost metering plane.
