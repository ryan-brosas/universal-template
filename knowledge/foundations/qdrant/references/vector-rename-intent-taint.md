<!-- capsule-v2 -->
# Vector-rename intent taint — how do you record "delete v then create v with a new schema" so the optimizer cannot keep stale storage?

**Source:** Qdrant Apache-2.0 `master@74f3e85b`; Codebase Memory `qdrant`. **Question:** A naive Create-or-Delete buffer collapses delete+recreate into plain create and silently preserves old vector bytes; what end-state representation prevents that?

## IntendedVector end-states with a sticky supersedes_wrapped flag
**Path/Symbol:** `lib/shard/src/proxy_segment/vector_name_changes.rs`: `IntendedVector` (:47-85), `record_create` (:101-127), `record_delete` (:130-133), `merge` (:361-390), `wrapped_carries_stale_schema` (:403-454).
**Signature:** `pub fn record_create(&mut self, vector_name: VectorNameBuf, config: VectorNameConfig, version: SeqNumberType, wrapped_config: &SegmentConfig)`.
**Data Shape:** `intent: AHashMap<VectorNameBuf, IntendedVector>`; `IntendedVector::Present { config, version, supersedes_wrapped: bool } | Absent { version }`.

### Decisive source
```rust
// :41-46 (module docs) — the bug being prevented:
// The previous representation was a Create-or-Delete pair stored in a HashMap,
// which silently collapsed `Delete v then Create v with a different schema` into
// a plain `Create v` and let the optimiser keep the stale storage from the wrapped
// segment.
// :108-117 — taint carries forward across intents:
let previous_taints = self.intent.get(&vector_name).is_some_and(IntendedVector::taints_wrapped);
let supersedes_wrapped =
    previous_taints || wrapped_carries_stale_schema(wrapped_config, &vector_name, &config);
// :75-84 — taints_wrapped = Absent | Present { supersedes_wrapped: true }
```

**Flow:** proxy records each named-vector op as an end-state intent → `Absent` marks the name deleted; `Present` computes `supersedes_wrapped` from (a) any earlier tainting intent for that name — "even a same-schema re-create cannot resurrect" wrapped data — or (b) schema mismatch against the wrapped config, which compares ONLY immutable user-controlled fields (dense size/distance/multivector_config/datatype; sparse modifier/index.datatype; dense↔sparse kind mismatch counts; absent name is not stale) while ignoring tunable HNSW/quantization settings → `merge` keeps the higher version per name but propagates taint from either side onto the winner.
**Invariant:** (1) the apply path must clear existing vector storage whenever `supersedes_wrapped` is set before installing the new config — idempotent create alone is insufficient; (2) taint is monotonic within a name: once wrapped data is logically discarded, no later same-schema intent can un-taint it; (3) merge never lowers versions nor loses taint.
**Probe:** no dedicated upstream unit test for `IntendedVector` transitions in this file (no `#[cfg(test)]` module); pinned by direct read of the whole file (:1-454) plus consumer reads of `create_vector_name`/`delete_vector_name` (`segment_entry.rs` :1080-1120). Recorded caveat in verification.md.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "qdrant", query: "IntendedVector supersedes wrapped record create delete vector name intent merge", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt end-state intent records with a sticky supersede/taint flag over op-pair buffers wherever idempotent creates can mask deletes. Adapt the immutable-field list to your schema's notion of identity. Omit qdrant's dense/sparse kind-mismatch special case if your host has one vector family.
