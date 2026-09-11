<!-- capsule-v2 -->
# MVCC GC incremental pass — how do you bound reclamation work so it never stalls the commit path?

**Source:** turso MIT `main@def9a060`; Codebase Memory `turso`. **Question:** What trigger, batching, and single-flight discipline let version-store GC run inline with commits?

## Threshold-triggered, chain-bounded, CAS-single-flighted sweep with pinned-LWM backoff
**Path/Symbol:** `core/mvcc/database/mod.rs:7089-7095` (`DEFAULT_GC_VERSION_THRESHOLD = 16*1024`, `MAX_CHAINS_PER_GC = 4096`), `CHAIN_SHRINK_MIN_CAPACITY = 16` (:7645 region), single-flight CAS + RAII reset, pinned-LWM short-circuit resetting the baseline ("so should_gc doesn't spin on every commit"), per-chain rules `gc_version_chain`.
**Signature:** incremental: commit → new-version count crosses threshold? → try CAS gc-in-progress flag (lose = skip) → process ≤4096 chains → reset flag in Drop.
**Data Shape:** reclaimable only when BOTH clocks allow (logical LWM AND physical materialization — see gc-two-clocks capsule); surviving chains shrink to capacity/4.

### Decisive source
```text
// mod.rs:7638 region + :9720-9722 — the two safety valves:
// "Tombstones without a committed current successor must survive, as must
//  versions already in the B-tree… Dropping the latter erases the only
//  evidence that a later delete must be written (#7638)."
// "over-resetting is safe: it only delays GC, never reclaims early"
```
The backoff subtlety: when the LWM is pinned (long-running reader), the pass exits WITHOUT work but also RESETS its trigger baseline — otherwise every subsequent commit sees threshold-exceeded and retries pointlessly. Batching by chains (not versions) keeps worst-case pause proportional to chain count; aborted-garbage drops unconditionally because no reader can ever need it.

**Flow:** commit increments version counter → threshold check (baseline-adjusted) → CAS single-flight → bounded chain sweep → capacity shrink → done.
**Invariant:** GC must be safe to SKIP entirely (correctness lives in the two-clock predicate, not the pass); single-flight or nothing — concurrent sweeps double-free; prefer delay over early free.
**Probe:** tests.rs:10485 builds 1 committed + 1023 garbage chain asserting dropped==1023/len==1/capacity shrink; finalized-tx cache pruning at :6910-6935.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "turso", query: "gc_version_chain should_gc MAX_CHAINS_PER_GC", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt trigger+batch+CAS-solo structure for any inline maintenance pass. Adapt constants to workload. Omit chain shrinking until memory pressure is observed.
