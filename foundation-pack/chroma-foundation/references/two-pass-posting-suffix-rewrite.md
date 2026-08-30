<!-- capsule-v2 -->
# Two-pass posting suffix rewrite — How does an incremental sparse commit avoid rewriting untouched blocks?

**Source:** Chroma Apache-2.0 `main@93652ec0869489b803fe1682427fc02bd47bec14`; Codebase Memory `ext-chroma`. **Question:** A delta touches a few offsets in one dimension — which blocks must be re-emitted, and in what ORDER do keys enter the blockfile?

## MaxScoreWriter::commit
**Path/Symbol:** `rust/index/src/sparse/maxscore.rs:MaxScoreWriter::commit` (:138-485); suffix selection via `partition_point` (:230-233); ordered-mutation debug assert (:160-165).
**Signature:** `pub async fn commit(self) -> Result<MaxScoreFlusher, MaxScoreError>`; writer state = `delta: DashMap<u32 /*dim*/, DashMap<u32 /*offset*/, Option<f32>>>` + optional old reader.
**Data Shape:** Blockfile keys: base64-encoded dim ids for posting blocks, `"d"+encoded_dim` for directory parts; directories store per-block max_offsets/max_weights (+v1 count).

### Decisive source
```rust
// Two-pass commit: posting blocks first (sorted by encoded_dim),
// then directory parts (sorted by dir_prefix). This satisfies the
// blockfile's ordered_mutations requirement since all "d"-prefixed
// directory keys sort after the plain base64 posting keys ...
debug_assert!(encoded_dims.iter().all(|(enc, _)| enc.as_str() < DIRECTORY_PREFIX), ...);
...
let first_affected = directory
    .max_offsets()
    .partition_point(|&max_off| max_off < min_affected_offset) as u32;
// Load only the suffix of posting blocks.
let suffix_blocks = reader.get_posting_blocks_range(encoded_dim, first_affected).await?;
...
let prefix_count = match stored_count {
    Some(old_count) => match (old_count as u64).checked_sub(suffix_old_len) {
        Some(count) => count,
        None => { /* underflow ⇒ corrupt: recount from prefix block headers */ }
    },
    None => reader.count_posting_entries_below(encoded_dim, first_affected).await?,
};
```

**Flow:** merge delta offsets with old entries from the suffix only → decompress suffix → apply updates/deletes (None=delete) → re-emit affected blocks; empty-dimension case deletes all old block seqs and drops the directory. Untouched PREFIX blocks ride along via the forked blockfile — they are never read or rewritten. Prefix count reconciles stored v1 count minus suffix length, with loud recount fallback on underflow or undecodable directory.
**Invariant:** Directory parts must be written AFTER their posting blocks (ordered_mutations); the debug assert pins the key-sort precondition. A dimension's directory and its posting blocks must agree on block boundaries after every commit.
**Probe:** `/tmp/chroma-p1/probe_battery.py` mx.suffix_rewrite / mx.ordered_assert anchors (GREEN); direct tests `rust/index/tests/maxscore/ms_03_writer_incremental.rs`, `ms_18_corrupt_directory.rs`, `ms_21_fork_cases.rs`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-chroma", query: "MaxScoreWriter commit suffix partition_point DIRECTORY_PREFIX ordered mutations", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt forked-write suffix rewriting plus write-order invariants for any LSM/LSM-like block store; adapt block sizes (`DEFAULT_BLOCK_SIZE=1024`, clamped to MAX_BLOCK_ENTRIES); omit the DashMap concurrency shape if your writer is single-threaded.
