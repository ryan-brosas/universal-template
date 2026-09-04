<!-- capsule-v2 -->
# Hash-build signature reuse — when does the emitter skip rebuilding a hash table?

**Source:** turso (Limbo) MIT `main@def9a060`; Codebase Memory project `turso`. **Question:** How does translate-time planning decide Reuse-vs-Build for a hash join's build side, and what identity makes two builds interchangeable?

## HashBuildPlanner typestate (prepare → emit)
**Path/Symbol:** `core/translate/main_loop/hash.rs:HashBuildPlanner::prepare` (:108, was :107 at `main@d9266124f`), `PreparedHashBuild::emit` (:261+), `expr_references_outer_query` (:19, was :18); program-side registry `core/vdbe/builder.rs:hash_build_signature_matches/has_hash_build_signature/clear_hash_build_signature` (:856/:867/:881, was :821-833).
**Signature:** `pub(super) fn prepare(self) -> Result<HashBuildPlan<'a,'plan>>` returning `HashBuildPlan::Reuse(HashBuildPayloadInfo)` or `HashBuildPlan::Build(Box<PreparedHashBuild>)`.
**Data Shape:** `HashBuildSignature { join_key_indices: Vec<usize>, payload_refs: Vec<MaterializedColumnRef>, key_affinities: String, use_bloom_filter, materialized_input_cursor: Option<CursorID>, materialized_mode }`; `HashBuildPayloadInfo { payload_columns, key_affinities, use_bloom_filter, bloom_filter_cursor_id, allow_seek }`.

### Decisive source
```rust
// core/translate/main_loop/hash.rs
let use_bloom_filter = self.hash_join_op.use_bloom_filter
    && collations.iter().all(|c| matches!(*c, CollationSeq::Binary | CollationSeq::Unset));
...
if self.program.hash_build_signature_matches(self.hash_table_id, &signature) {
    return Ok(HashBuildPlan::Reuse(HashBuildPayloadInfo { ... }));
}
if self.program.has_hash_build_signature(self.hash_table_id) {
    self.program.emit_insn(Insn::HashClose { hash_table_id: self.hash_table_id });
    self.program.clear_hash_build_signature(self.hash_table_id);
}
Ok(HashBuildPlan::Build(Box::new(PreparedHashBuild { planner: self, config: ... })))
```
Materialized build inputs (`materialized_build_inputs[build_table_idx]`) switch payload to `MaterializedBuildInputMode::KeyPayload { num_keys, payload_columns }` with `allow_seek=false`, vs fresh builds deriving payload from the FULL `col_used_mask` of the build table. Key affinities come from `comparison_affinity(build_expr, probe_expr)` per key; collations from `resolve_comparison_collseq_with_symbols(...).unwrap_or(Binary)`.

**Flow:** derive affinities/collations → pick payload shape (materialized KeyPayload vs col_used_mask) → assemble signature → exact-match reuse; else close stale build if any and emit fresh (build loop + optional bloom filter cursor).
**Invariant:** Signature equality includes payload COLUMN REFS and affinities — reusing a build whose stored columns differ from what THIS probe consumes reads garbage; bloom filter is silently disabled for non-binary collations (NOCASE hashing exists in the executor but emission gates it off here).
**Probe:** text anchors: `grep -c 'hash_build_signature_matches' core/vdbe/builder.rs` → 1; `grep -c 'HashClose' core/translate/main_loop/hash.rs` → 1; `grep -c 'use_bloom_filter = self.hash_join_op.use_bloom_filter' core/translate/main_loop/hash.rs` → 1.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "turso", query: "HashBuildPlanner HashBuildSignature prepare", limit: 10 });
```

## Verdict
Adopt the signature-reuse protocol and the bloom-filter collation gate; adapt MaterializedColumnRef to host column-ref plumbing; probe-side machinery (emit_probe/install_context :586-914) belongs to the executor twin capsule vdbe-hash-join-grace-spill.
