<!-- capsule-v2 -->
# B-tree balancing bounds — what blast-radius limits and append fast-path gate the general rebalancing algorithm?

**Source:** turso (Turso) MIT `main@f1800bb8c` (re-anchored from `def9a060`); Codebase Memory `turso`. **Question:** When does balancing run, within which structural bounds, and why does the sequential-append workload bypass it?

## 3→5 asserted bound, ⅔-full trigger, balance_quick fast path
**Path/Symbol:** constants `MAX_SIBLING_PAGES_TO_BALANCE=3`, `MAX_NEW_SIBLING_PAGES_AFTER_BALANCE=5` `core/storage/btree.rs:147/:150`; enforcement assert "it is corrupt to require more than 5 pages to balance 3 siblings" (:3862); trigger `free_space * 3 > usable_space * 2` (:2994, :6837; naive-algorithm honesty note :3035-3037 incl. "Sqlite tries to have a page at least 40% full"); `balance_quick` gate (:3167+, divider array :3220); cursor saves seek key across rebalance.
**Signature:** quick path fires only when ALL hold: table leaf ∧ exactly one overflow cell ∧ cell is last ∧ parent isn't page 1 ∧ leaf is parent's rightmost child.

### Decisive source
```rust
/// We only need maximum 5 pages to balance 3 pages, because we can guarantee that cells from 3 pages will fit in 5 pages.
pub const MAX_NEW_SIBLING_PAGES_AFTER_BALANCE: usize = 5;
```
(btree.rs:149-150; the bound is ENFORCED at :3862 — violation becomes corruption detection instead of fixed-array overflow)
```rust
let mut new_divider: [u8; 13] = [0; 13]; // 4 bytes for page number, max 9 bytes for rowid (varint)
```
(:3220)

**Flow:** overflow insertion OR overwrite/delete dropping below ~⅔ full → already-balanced gate (cites sqlite btree.c#L9064-L9071) → quick path if eligible: allocate ONE new rightmost leaf + insert a ≤13-byte divider (4B page pointer + max 9B varint rowid) — the dominant sequential-rowid-append workload never runs the general algorithm → else `balance_non_root`. The cursor SAVES its seek key before any balancing because rebalancing invalidates position, and re-seeks afterward.
**Invariant:** Bound the blast radius structurally AND assert the bound (corruption detection beats memory unsafety); special-case the common pattern first so the general path handles rare cases and its invariants stay checkable.

**Probe:** `core/storage/btree.rs:13225 test_delete_balancing` inserts 10k rows, deletes keys 500..=3500 to force underfull pages through FULL balancing, then asserts survivor/deleted key sets plus recursive validate_btree(); rightmost-leaf splits via balance_quick exercised around :13529.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "turso", query: "balance_non_root balance_quick MAX_NEW_SIBLING_PAGES_AFTER_BALANCE", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the asserted 3→5 bound, the ⅔ trigger, and the append fast-path gating order. Adapt thresholds to page size; omit balance_quick until you have rowid-table workloads that reward it.
