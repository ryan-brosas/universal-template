<!-- capsule-v2 -->
# B-tree rebalancing — what bounds the blast radius, and why does the append fast path exist?

**Source:** turso (Limbo) MIT `main@1654d1587`; Codebase Memory `turso`. **Question:** How do I rebalance SQLite-compatible b-tree pages without unbounded rewrites, and when can I skip the general algorithm?

## Proven 3→5 bound + balance_quick append path
**Path/Symbol:** `core/storage/btree.rs` constants :147/:150 (`MAX_SIBLING_PAGES_TO_BALANCE = 3`, `MAX_NEW_SIBLING_PAGES_AFTER_BALANCE = 5`), assert :3862, trigger gate `free_space * 3 > usable_space * 2` :2994, honesty note :3035-3037, sqlite citation comment :3068, `balance()` entry :3043, `balance_non_root` :3245, quick-path gate comments :3103-3146, `fn balance_quick` :3167 (13-byte divider construction :3220), peer-append test coverage at :13508-13530.
**Signature:** on overflow/underflow, up to 3 adjacent pages are gathered under one parent and redistributed into at most `MAX_NEW_SIBLING_PAGES_AFTER_BALANCE = 5` pages. Balancing triggers on overflow insertion, or after overwrite/delete when the page drops below ~2/3 full (`free_space * 3 > usable_space * 2`).
**Data Shape:** cursor saves its seek key before any balancing (rebalancing invalidates position) and re-seeks afterward.

### Decisive source
```text
// btree.rs:150 — the bound is proven, not guessed:
//   "We only need maximum 5 pages to balance 3 pages, because we can guarantee
//    that cells from 3 pages will fit in 5 pages."
// :3862 — and it is ENFORCED:
//   an assert ("it is corrupt to require more than 5 pages to balance 3
//   siblings") turns a violation into corruption detection instead of a
//   fixed-array overflow.
```

Balancing is NOT run on every write. The dominant real workload — sequential rowid appends — gets `balance_quick`, which fires only when ALL hold (:3103-3146 gate): table leaf, exactly one overflow cell, that cell is last, parent isn't page 1, leaf is the parent's rightmost child. It allocates one new rightmost leaf and inserts a divider no longer than 13 bytes — `[u8; 13] = 4-byte page number + max 9-byte varint rowid` (:3220). Honesty note at :3035-3036: "This is a naive algorithm that doesn't try to distribute cells evenly by content… Sqlite tries to have a page at least 40% full"; an already-balanced rationale cites sqlite btree.c#L9064-L9071 before any work starts (:3068).

The concurrency constants block lives in **`core/storage/wal.rs`:2424-2434** (NOT btree.rs — earlier drafts mis-cited the file): `CKPT_BATCH_PAGES = 512` ("IOV_MAX is 1024 on most systems, lets use 512 to be safe"), `MIN_AVG_RUN_FOR_FLUSH = 32.0`, `MIN_BATCH_LEN_FOR_FLUSH = 512`, `MAX_INFLIGHT_WRITES = 64`, `MAX_INFLIGHT_READS = 512`, `IOV_MAX = 1024` — under a loud TODO: "*ALL* of these need to be tuned for perf." Every number trades a named failure for throughput; WAL batch appends assert `pages.len() <= IOV_MAX` (wal.rs:4352/4504). **Lesson: pin every concurrency budget to a named constant beside the comment explaining the failure it prevents — and admit loudly (TODO) when a number is a guess.**

**Flow:** write → overflow or <2/3-full gate → gather ≤3 siblings → redistribute into ≤5 asserted pages → cursor re-seek; appends take the quick path first.
**Invariant:** never let redistribution need more than 5 pages (assert it); never run full balancing where the append preconditions hold.
**Probe:** from repo root: `grep -c 'MAX_SIBLING_PAGES_TO_BALANCE: usize = 3' core/storage/btree.rs` → 1; `sed -n '3862p' core/storage/btree.rs | grep -c 'corrupt to require more than 5 pages'` → 1; `grep -c 'let mut new_divider: \[u8; 13\]' core/storage/btree.rs` → 1; `grep -c 'Peer appends: balance_quick allocates a new rightmost leaf' core/storage/btree.rs` → 1. Direct test `test_delete_balancing` (:13225) inserts 10k rows (:13238), deletes keys 500..=3500 (:13265) forcing underfull pages through full balancing, asserts survivor/deleted key sets via `cursor.exists` sweeps plus recursive `validate_btree` (:13259).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "turso", query: "MAX_SIBLING_PAGES_TO_BALANCE balance_quick", limit: 10 });
```

## Verdict
Adopt the structural 3→5 bound with its assert and the append fast path verbatim; adapt trigger thresholds to your fill-factor targets; omit quick-balance if you have no rowid-append workload. Coverage caveat: none material. Pin note: all line numbers re-verified against `main@1654d1587` after the min-cell-size drift wave (pass 15); `balance_quick`'s own span survived both waves unchanged (:3167).
