<!-- capsule-v2 -->
# Sibling redistribution legality — why does greedy cell packing need a mandatory second pass?

**Source:** turso (Turso) MIT `main@f1800bb8c` (re-anchored from `def9a060`); Codebase Memory `turso`. **Question:** After collecting sibling cells into one array and packing greedily, which post-passes are correctness (not optimization), and which index-skew traps bite?

## Legality repair + virtual-vs-physical index skew
**Path/Symbol:** `core/storage/btree.rs balance_non_root` (:3245+ @f1800bb8c): greedy pack → mandatory right-to-left adjustment (:3959-3962 comment, loop :3963+); OVERFLOW CELL ADJUSTMENT (:3371-3393, formula :3383); two-pass safe update order (:4395-4428 region, quote block :4380-4403); root-collapse defragment rule (:4484-4503); post-balance validation harness (`post_balance_non_root_validation` :4641+).
**Data Shape:** Flat CellArray of all cells from up to three siblings + parent dividers; dividers differ by page type — interior keep payload and repoint left child; table-leaf reuse the moved rowid; index-leaf prepend the new page id to the stripped key. Page numbers reassigned so physical file order matches logical order.

### Decisive source
```rust
// :3959-3962 — This adjustment is more than an optimization.  The packing above might
// be so out of balance as to be illegal. For example, the right-most
// sibling might be completely empty. This adjustment is not optional.
```

And the skew trap, verbatim consequence: drop_cell() physically shifts cell-pointer slots left while insert_into_cell() stores overflow cells virtually — "'3' is actually physically located at index '2'. So IF the parent has an overflow cell, we need to subtract 1" (:3380-3385). Miss this and sibling loads read the WRONG child pointer after InteriorNodeReplacement (:3371-3393).

**Flow:** gather → greedy left-to-right pack → right-to-left legality repair (move back while it improves balance) → redistribute with two-pass update ordering (downward+upward passes over `done[]` mask; when cells move left, update the LEFT sibling before the target page — mid-redistribution readers must never see rewritten bytes, :4395-4428) → root collapse defragments the child BEFORE copying into the parent ("if the parent is page 1 then it will [be] smaller than the child due to the database header", :4498-4503).
**Invariant:** Illegal states (empty rightmost sibling, fanout violation) are repaired by explicit post-passes whose comments SAY they are not optional — never by trusting greedy packing.

**Probe:** Debug builds run `post_balance_non_root_validation` (:4641+): snapshot every cell pre-redistribution, verify byte-exact survival, no self/parent-pointing children, every new page reachable from a divider or rightmost pointer. Property tests `prop_insertions_preserve_exact_cell_bytes` / `prop_defragment_fast_matches_full` (:14064/:14263) pin freeblock ordering and compute_free_space accounting.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "turso", query: "balance_non_root post_balance_non_root_validation OVERFLOW CELL ADJUSTMENT", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt greedy-packing-plus-legality-repair as a pair (one without the other corrupts); adopt the documented virtual-vs-physical index conversion discipline. Adapt CellArray representation; omit index-leaf divider prepending until you port index btrees.
