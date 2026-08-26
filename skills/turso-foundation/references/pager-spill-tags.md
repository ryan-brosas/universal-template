<!-- capsule-v2 -->
# Spill write-back tags — how does an async WAL write survive concurrent mutation of the same page?

**Source:** turso (MIT) @ main`def9a060`; Codebase Memory `turso`. **Question:** How do I prevent an in-flight async page write from marking a NEWER in-memory version durable?

## TAG_WRITE_PENDING + compare-on-completion
**Path/Symbol:** sentinels + bit layout live in `core/storage/pager.rs` (:703-731 at HEAD: `TAG_UNSET = u64::MAX` / `TAG_WRITE_PENDING = MAX−1` at :703-706, epoch:20/frame:44 layout at :710-714, `PageInner.wal_tag` field at :111+); spill marks victims BEFORE IO (:943/:961 region); completion filter (:3924 "page {} modified during write, not marking as spilled"); set_dirty clears tag+spilled together (:807-816); checkpoint validity (:991). NOTE: an earlier revision of this capsule attributed wal_tag packing to btree.rs — that was a legacy-prose carry-over; the type lives in pager.rs.
**Signature:** each page records WHICH WAL frame version it holds in a single u64 `wal_tag` — 44-bit frame number + 20-bit checkpoint epoch — bracketed by two sentinels: `TAG_UNSET (=u64::MAX)` and `TAG_WRITE_PENDING (=MAX−1)`, "set before starting a WAL write so we can detect if page was modified during the write."
**Data Shape:** PAGE_DIRTY keeps the page unevictable; PAGE_SPILLED (added after successful write) makes it evictable.

### Decisive source
The hazard this kills: an async WAL write of page P is in flight while the btree mutates P again. If the completion blindly stamped the new frame tag and cleared dirty, the newer in-memory version would be considered durable and the page evictable — lost writes.

```text
// btree.rs:3965-4005 / :3810+ — the protocol:
//   spill marks all victims TAG_WRITE_PENDING BEFORE issuing IO;
//   on completion, only pages whose tag survived get marked spilled —
//   ":3810+ logs 'page {} modified during write, not marking as spilled'"
//   and warns when NOTHING survived.
// :807-816: set_dirty() clears tag and spilled flag together —
//   "Clear spilled flag since page is being modified again."
```

The epoch bits exist because checkpoint_seq rotates WAL generations: a stale frame number from a previous generation must never satisfy a checkpoint. Commit-time verification (`is_valid_for_checkpoint`, :984-996) requires frame==target && epoch==current && !dirty && loaded && !locked.

**Flow:** dirty page under cache pressure → stamp TAG_WRITE_PENDING → issue async WAL write → completion compares tag → survivors become spilled/evictable; mutated pages stay dirty and retry later.
**Invariant:** pair a write-in-flight sentinel with compare-on-completion so concurrent mutation downgrades to "retry later" instead of false durability; pack generation + position into one atomically-swapped word.
**Probe:** arm_spill_yield_on_read + SpillYieldHook (:1450-1487) inject deterministic yields; process_overflow_read_survives_spill_yield_from_next_chain_read (~11950) asserts byte-exact record reconstruction across an injected chain-read yield.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "turso", query: "wal_tag TAG_WRITE_PENDING spilled", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt sentinel + compare-on-completion verbatim for any async write-back cache; adapt bit-packing to your generation counts; omit epoch bits if your log never rotates generations. Coverage caveat: none material.
