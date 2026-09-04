<!-- capsule-v2 -->
# Commit dependencies — how do readers speculate against a Preparing writer without blocking?

**Source:** turso MIT `main@def9a060`; Codebase Memory `turso`. **Question:** How does a transaction read a version whose deleter is still preparing — and still commit safely if that deleter aborts?

## Counted speculation resolved at the commit boundary
**Path/Symbol:** `core/mvcc/database/mod.rs:1012-1054` (`commit_dep_counter: AtomicU64`, `commit_dep_set: Mutex<HashSet<TxID>>`), register/drain logic :9940-9995 region + :3281-3296, wait state `WaitForDependencies` :1425-1436 & :2938-2965.
**Signature:** `fn register_commit_dependency(...)` increments own counter then inserts own tx_id into the writer's set; commit waits for counter == 0.
**Data Shape:** per-tx: one atomic u64 counter + one mutex'd set of tx ids that depend on me. Hekaton §3.2 quoted in-source: "If T passes validation, it must wait for outstanding commit dependencies to be resolved."

### Decisive source
```rust
// ordering trap, mod.rs:~2918-2926 (CommitState::WaitForDependencies)
// ** - WaitForDependencies checks AbortNow and waits for counter == 0.
```
Three correctness details the source calls out explicitly:
1. **Acyclicity is structural**: dependency edges always go from higher end_ts to lower end_ts, so the wait graph cannot cycle (:2905-2910 region).
2. **Memory-ordering trap**: check `abort_now` AFTER observing counter==0. Rollback stores abort_now with Release *before* decrementing with AcqRel, so an Acquire load of zero synchronizes with the store. Check in the opposite order and you can observe `(false, 0)` and wrongly commit an aborting dependant.
3. **Underflow guard**: increment the counter BEFORE inserting into the set and before dropping the lock (:9975-9980 region) — otherwise an abort drain racing registration wraps 0 → u64::MAX.

Even read-only commits must drain dependencies (:2840-2852): a SELECT may have speculated against a Preparing writer, so its fate is coupled too. Cascade abort: when a depended-on tx aborts it takes its dep_set, sets each dependent's `abort_now`, and decrements their counters (:3281-3296).

**Flow:** speculative read sees Preparing-deleter's version (or speculatively ignores such a deletion) → registers dependency → proceeds lock-free → writer commits ⇒ deps resolve silently; writer aborts ⇒ cascade abort flips `abort_now` and drains counters.
**Invariant:** increment-before-insert ordering AND check-abort-after-counter-zero are not tunable — they ARE the algorithm; both orderings have named failure modes (underflow wrap, TOCTOU commit).
**Probe:** tests.rs:6940 asserts a speculative read is visible AND leaves `commit_dep_counter==1` with dep_set={2}; tests.rs:6974 asserts cascade abort flips abort_now and drains to 0.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "turso", query: "commit_dep_counter register_commit_dependency WaitForDependencies", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt counted-dependency speculation wholesale for any optimistic MVCC port. Adapt set storage (HashSet vs intrusive list). Omit nothing from the three ordering details — each guards a demonstrated race. Coverage caveat: probes cite legacy line numbers; re-pin by symbol name before running.
