<!-- capsule-v2 -->
# PackedTs version model — how do row versions encode liveness without locks?

**Source:** turso MIT `main@def9a0601b8ead82675e672e1843447251b15fb4`; Codebase Memory `turso`. **Question:** How does a porter represent "version visible from X until Y" when both endpoints can be either a committed timestamp OR an in-flight transaction id?

## Tagged-u64 begin/end pair + one atomic word of transaction fate
**Path/Symbol:** `core/mvcc/database/mod.rs:408-446` (`PackedTs`, `TIMESTAMP_TAG`, `TXID_TAG`) and `mod.rs:1337-1354` (`TransactionState::encode`, `PREPARING_BIT`, `COMMITTED_BIT`).
**Signature:** `const TIMESTAMP_TAG: u64 = 1 << 62; const TXID_TAG: u64 = 1 << 63;` / `fn pack(Option<TxTimestampOrID>) -> PackedTs`.
**Data Shape:** Every `RowVersion` carries `begin: PackedTs`, `end: PackedTs`; transaction fate is ONE `AtomicU64` per tx: Active / Preparing(ts) / Committed(ts) / Aborted / Terminated, with the two tag bits above a 62-bit timestamp mask.

### Decisive source
```rust
// mod.rs:408-409 (inside impl PackedTs)
const TIMESTAMP_TAG: u64 = 1 << 62;
const TXID_TAG: u64 = 1 << 63;
```
> "The two distinct tag bits (rather than a zero sentinel) are required because Timestamp(0) is a real value - the logical clock hands out timestamp 0 to the first transaction." (mod.rs:393-399 region, comment block above PackedTs)

During a transaction's active phase its new versions carry its **TxID** in `end` (deletes) / `begin` (inserts); after commit the `RewriteLiveVersions` step rewrites them to the commit **Timestamp** in chunks (`MVCC_COMMIT_BATCH_SIZE = 1024`, mod.rs:1514). Visibility reduces to two predicates — `is_begin_visible && is_end_visible` — where committed-Timestamp arms assert strict monotonicity ("begin_ts and committed rv_begin_ts cannot be equal") and TxID arms look up the creator/deleter state (live map first, then `finalized_tx_states` cache), falling through conservatively (begin invisible, end visible). Turso corrects a typo in the Hekaton paper itself (mod.rs:10173, citing avi.im/blag/2023/hekaton-paper-typo): a version whose end field is a TxID is visible only when that TxID is not your own.

**Flow:** insert/update versions packed with TxID refs → commit assigns end_ts under the clock lock → `RewriteLiveVersions` re-packs TxIDs to Timestamps chunk-by-chunk while readers resolve unresolved TxIDs via `txs[tx_id]` (now Committed).
**Invariant:** zero is never a sentinel — discrimination is by tag bit; a port that treats `PackedTs(0)` as NULL breaks timestamp 0.
**Probe:** `core/mvcc/database/tests.rs` hand-builds transactions/versions asserting `is_visible_to` against Hekaton Tables 1 & 2 (legacy probe range tests.rs:6678-6815 — re-pin by symbol name `is_visible_to` if ranges drift); hermitage G1a/G1b cover aborted/intermediate visibility.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "turso", query: "PackedTs pack TIMESTAMP_TAG", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the tagged-u64 pair + single-atomic-word fate encoding verbatim — it is the lock-free substrate every other MVCC capsule builds on. Adapt the tag-bit positions to your word size. Omit nothing here; omitting either tag forces a sentinel collision with Timestamp(0). Coverage caveat: line ranges shift fast in this 10k-line file — cite by symbol name.
