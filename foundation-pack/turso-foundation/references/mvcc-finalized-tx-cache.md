<!-- capsule-v2 -->
# MVCC finalized-tx cache — how does visibility checking stay O(1) when most referenced transactions are long gone?

**Source:** turso MIT `main@def9a060`; Codebase Memory `turso`. **Question:** Where do visibility predicates resolve a TxID whose transaction no longer sits in the live map — and how does the cache itself get garbage collected?

## finalized_tx_states SkipMap beside the live map, pruned by the GC pass
**Path/Symbol:** `core/mvcc/database/mod.rs` (`finalized_tx_states: SkipMap<TxID, TransactionState>` field :1010-1011 region; lookup helper `lookup_tx_state(txs, finalized_tx_states, tx_id)` used by `is_write_write_conflict` :9797 and visibility arms), pruning probed at tests.rs:6910-6935.
**Signature:** `lookup_tx_state(live_map, finalized_cache, id) -> Option<TransactionState>` — live map FIRST (authoritative for active/preparing), then finality cache.
**Data Shape:** cache stores terminal states only (Committed(ts)/Aborted/Terminated) as plain values; entries are safe to drop ONLY below the LWM clock, since a snapshot at or above it can never reference them.

### Decisive source
```text
// Visibility/conflict arms consult BOTH maps in one order (mod.rs:9797-9821):
//   match lookup_tx_state(&self.txs, &self.finalized_tx_states, rv_end) {
//       Some(TransactionState::Aborted | Terminated) => false,
//       Some(Active | Preparing | Committed) => true,
//       None => /* conservative: treat unknown as conflict */,
```
The two-map split is what makes lock-free resolution possible: fate is immutable once terminal, so a cached Committed(42) never needs invalidation — only reclamation. The conservative-unknown arm exists precisely BECAUSE the cache is eventually pruned: a reader old enough to reference a pruned tx must fail toward conflict/aborted, never toward visibility. Pruning runs with GC (tests.rs:6910-6935 region) under the same LWM discipline.

**Flow:** predicate hits TxID ref → live map? resolved live | finality cache? resolved terminal | neither ⇒ conservative arm.
**Invariant:** terminal states are write-once; prune only below LWM; unknown must degrade to conflict/invisible-begin, never to visible.
**Probe:** tests.rs:6910-6935 (cache pruning); hermitage G1a/G1b pin aborted-invisibility end-to-end.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "turso", query: "finalized_tx_states lookup_tx_state", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the immutable-terminal cache + live-map-first ordering for any optimistic system whose history outlives its participants. Adapt storage to your map type. The conservative-unknown arm is NOT optional if you ever prune.
