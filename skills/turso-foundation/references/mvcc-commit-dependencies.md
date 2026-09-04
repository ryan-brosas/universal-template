<!-- capsule-v2 -->
# Counted commit dependencies — how do readers speculate past Preparing writers without blocking?

**Source:** turso (MIT) `main@def9a0601b8e` ($REFERENCE_ROOT/memory/turso); Codebase Memory project `turso`. **Question:** How must dependency registration, draining, and the memory orderings be wired so speculative reads stay safe?

## Register instead of wait; drain before you may commit
**Path/Symbol:** `core/mvcc/database/mod.rs`: `register_commit_dependency` (:9940-9995 region; fn at :9982 at HEAD), speculative visibility arms (:10120-10195), tombstone handling (:9820-9850), cascade-abort drain (:3281-3296: dep_set drained, each dependent gets abort_now=true, counters decremented), `WaitForDependencies` step (:2886-2965); read-only commits also drain (:2840-2852).
**Signature:** `commit_dep_counter: AtomicU64` per transaction + `commit_dep_set` (tx_ids depending on me) — both on Transaction (:1012-1054); `fn register_commit_dependency(...)`.
**Data Shape:** when a reader speculatively reads a version whose deleter is still Preparing (or speculatively ignores such a deletion), ITS counter increments and its tx_id enters THE WRITER's dep_set. A transaction cannot commit until its counter drains to zero; if something it depended on aborts, `abort_now` is set and it rolls back too. Hekaton §2.7 register-and-report quoted in-source (:9977-9981): "To take a commit dependency on a transaction T2, T1 increments its CommitDepCounter and adds its transaction ID to T2's CommitDepSet." — "The lock on `commit_dep_set` serializes with the drain in commit/abort resolution, preventing the race where we push an entry after the drain." Live-map removal asserts an EMPTY dependency set — otherwise "those dependencies would wait forever (deadlock)."

### Decisive source
```rust
// Three correctness details easy to get wrong (all cited verbatim in mod.rs):
// 1) Acyclicity is structural (:2905-2910): "edges always go from higher end_ts
//    to lower end_ts, so the wait graph is acyclic."
// 2) Memory-ordering trap (:2918-2926): check `abort_now` AFTER observing
//    counter==0. Rollback stores abort_now with Release BEFORE decrementing with
//    AcqRel, so an Acquire load of zero synchronizes with it. Check in the
//    opposite order and an aborting dependency slips between your two reads —
//    you see (false, 0) and wrongly commit.
// 3) Underflow guard (:9975-9980): increment the counter BEFORE inserting into
//    the set and before dropping the lock, or an abort drain can wrap 0 to u64::MAX.
```

**Flow:** speculate → register (counter++ under lock, id into writer's set) → writer commits or aborts → dependents' counters drain → committer waits for zero → checks abort_now (in THAT order) → commits or cascades rollback. Even READ-ONLY commits must drain: a SELECT may have speculated against a Preparing writer.
**Invariant:** edge orientation (higher→lower end_ts) makes the wait graph structurally acyclic — break it and you reintroduce deadlock that counting cannot see.
**Probe:** `core/mvcc/database/tests.rs:6940` asserts a speculative read is visible AND leaves counter==1 with dep_set={2}; `tests.rs:6974` asserts cascade abort flips abort_now and drains to 0.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "turso", query: "register_commit_dependency commit_dep_counter WaitForDependencies", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt counted dependencies resolved at commit boundaries as the alternative to reader-writer blocking. Adapt the u64 counter type freely; DO NOT adapt the ordering of increment/drain/check — those orderings ARE the algorithm. Omit the finalized_tx_states cache only with the same caveat as the version-model capsule.
