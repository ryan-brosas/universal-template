<!-- capsule-v2 -->
# Spill tags & async write-back — how does a dirty-page cache survive writes in flight while the b-tree mutates again?

**Source:** turso (Turso) MIT `main@def9a0601b8ead82675e672e1843447251b15fb4`; Codebase Memory `turso`. **Question:** How do you prevent an async WAL write's completion from falsely stamping a NEWER in-memory version as durable?

## Write-in-flight sentinel + compare-on-completion + packed generation word
**Path/Symbol:** `TAG_UNSET = u64::MAX` / `TAG_WRITE_PENDING = u64::MAX − 1` `core/storage/pager.rs:703-706`; bit layout epoch:20/frame:44 (`EPOCH_BITS=20`, :711-712); spill marking victims PENDING BEFORE IO (:943/:961 region); completion filter (:3924); set_dirty clears tag+spilled together (:807-816); checkpoint validity (:991); deterministic yield injection `SpillYieldHook` (:1472) + `arm_spill_yield_on_read` (:3445).
**Data Shape:** One atomic u64 `wal_tag` per page packs 44-bit frame number + 20-bit checkpoint epoch (max epoch 1048576), bracketed by two sentinels.

### Decisive source
```rust
/// WAL write in progress, sentinel value set before starting a WAL write
/// so we can detect if page was modified during the write
pub const TAG_WRITE_PENDING: u64 = u64::MAX - 1;
```
(pager.rs:705-706; completion side logs "try_spill_dirty_pages: page {} modified during write, not marking as spilled" and warns when NOTHING survived, :3924)

**Flow:** cache pressure spills dirty page → mark ALL victims TAG_WRITE_PENDING BEFORE issuing IO → page stays PAGE_DIRTY but gains PAGE_SPILLED (now evictable) → async write completes → only pages whose tag STILL equals the written version get marked spilled; any page mutated mid-flight keeps dirty and retries later → set_dirty() clears tag and spilled flag TOGETHER.
**Invariant:** The failure being killed: if completion blindly stamped the new frame tag and cleared dirty, the newer in-memory version would be considered durable and the page evictable — LOST WRITES. Concurrent mutation must downgrade to "retry later," never false durability. The epoch bits exist because checkpoint_seq rotates WAL generations: a stale frame number from a previous generation must NEVER satisfy a checkpoint (`is_valid_for_checkpoint(target_frame, epoch)` requires frame==target && epoch==current && !dirty && loaded && !locked, :991).

**Probe:** `arm_spill_yield_on_read` (:3445) + `SpillYieldHook` (:1472) inject deterministic yields mid-spill; tests drive process_overflow read paths across injected chain-read yields asserting byte-exact record reconstruction (pager.rs test module).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "turso", query: "wal_tag TAG_WRITE_PENDING is_valid_for_checkpoint PAGE_SPILLED", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the sentinel + compare-on-completion pair and the single packed generation word. Adapt bit splits to your frame-number domain. Omit encryption/XOR layers (separate concern); do NOT omit the pending sentinel — plain timestamp stamping loses writes.
