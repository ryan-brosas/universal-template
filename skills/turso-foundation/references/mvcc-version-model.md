<!-- capsule-v2 -->
# MVCC version model — how are row versions and transaction fates encoded so concurrency checks need no locks?

**Source:** turso (MIT) `main@def9a0601b8e` (/mnt/hdd/utopia/inspo/memory/turso); Codebase Memory project `turso`. **Question:** What must a porter encode per row version so visibility decisions reduce to lock-free lookups?

## Two tagged u64s per boundary + one atomic fate word
**Path/Symbol:** `core/mvcc/database/mod.rs`: `PackedTs` (:393-446), `TransactionState::encode` (:1308-1400).
**Signature:** `PackedTs { bits: u64 }` with tag bits `TIMESTAMP_TAG = 1<<62`, `TXID_TAG = 1<<63`; `TransactionState::encode() -> u64` with `PREPARING_BIT` / `COMMITTED_BIT` above a 62-bit timestamp mask.
**Data Shape:** every row version carries `begin` and `end`, each ONE bit-packed u64 holding either a committed Timestamp or an in-flight TxID, discriminated by tag bits. Zero is a REAL value (the logical clock hands out timestamp 0 to the first transaction), which is why two distinct tag bits exist rather than a zero sentinel.

### Decisive source
```rust
// mod.rs:393-399 — Layout (top two bits are the tag):
// * `0`                  → `None`
// * `(1 << 62) | value`  → `Some(Timestamp(value))`
// * `(1 << 63) | value`  → `Some(TxID(value))`
// `value` occupies the low 62 bits.
```

**Flow:** during a transaction's active phase its new versions track its TxID; after commit the RewriteLiveVersions commit-machine step rewrites them to the commit Timestamp in chunks (mod.rs:808-826 documents the switch). Visibility of a version to a reader reduces to two predicates, `is_begin_visible && is_end_visible` (mod.rs:10090-10240): committed-Timestamp arms assert strict monotonicity ("begin_ts and committed rv_begin_ts cannot be equal"); TxID arms look up creator/deleter state (live map first, then a `finalized_tx_states` cache) and fall through CONSERVATIVELY — begin invisible, end visible.
**Invariant:** a version whose end field is a TxID is visible only when that TxID is not the reader's own — turso corrects a typo in the Hekaton paper itself here (mod.rs:10182-10186). Transaction fate lives in exactly one atomic u64; no other word decides Committed/Aborted.
**Probe:** `core/mvcc/database/tests.rs:6678-6815` hand-builds transactions and versions and asserts `is_visible_to` outcomes against Hekaton's Tables 1 and 2; tag constants verified at :408-409 inside impl PackedTs (`const TIMESTAMP_TAG: u64 = 1 << 62; const TXID_TAG: u64 = 1 << 63;`); hermitage suite (`core/mvcc/database/hermitage_tests.rs`) pins G1a/G1b aborted/intermediate visibility end-to-end.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "turso", query: "PackedTs is_visible_to TransactionState encode", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the tagged-u64 (begin,end) pair + single atomic fate word as the portability core — every concurrency decision becomes a lock-free state lookup. Adapt the specific tag-bit layout if your timestamps fit narrower words. Omit the finalized_tx_states cache until profiling shows the live-map lookup matters. No coverage caveat: tests.rs walks both tables of the paper.
