<!-- capsule-v2 -->
# SkipList — what is the lock-free ordered-map primitive the MVCC store builds on?

**Source:** turso (MIT) @ main`def9a060`; Codebase Memory `turso`. **Question:** How do I implement a concurrent ordered map whose lookups never block, for use as the live-transaction and version-chain index?

## skiplist::{map,set} over a base tower
**Path/Symbol:** `core/skiplist/base.rs` (2528L), `map.rs` (963L), `set.rs` (738L), `comparator.rs`, `equivalent.rs`, `mod.rs` (263L).
**Signature:** `SkipMap<K, V, C, A>` / `SkipSet`; the MVCC store uses them for the live transaction map and version chains (mod.rs `txs: &SkipMap<TxID, Transaction, BasicComparator, A>`). Comparator and allocator are generic parameters; `BasicComparator` orders by value.
**Data Shape:** nodes form a probabilistic tower; `Equivalent` trait supplies equivalence for lookups distinct from ordering.

### Decisive source
```rust
// mod.rs:9982+ — the store's usage shape:
// register_commit_dependency(txs: &SkipMap<TxID, Transaction<A>, BasicComparator, A>, …)
//   — the live transaction map is a SkipMap; GC and visibility consult it
//     lock-free.
```
The skiplist layer is what makes "every concurrency decision a lock-free state lookup" (see mvcc-version-model) physically true: lookups walk the tower without taking the store's write lock, so readers never block writers.

**Flow:** insert/remove/iterate over the tower with per-level CAS; lookups descend from the top level; comparator decides ordering, equivalent decides match.
**Invariant:** the store must treat the SkipMap as the authoritative live set — never duplicate it under a lock that would reintroduce blocking.
**Probe:** `core/skiplist/map_tests.rs` (1181L), `base_tests.rs` (1063L), `set_tests.rs` (835L) — direct unit suites for the primitive.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "turso", query: "SkipMap SkipSet skiplist comparator", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the lock-free ordered-map primitive for any hot concurrent index; adapt tower height/randomization to your concurrency; omit if your language has a battle-tested equivalent (the VALUE here is the lock-free lookup contract, not the skiplist itself). Coverage caveat: probes are the in-file unit suites; no dedicated behavioral test beyond them this pass.
