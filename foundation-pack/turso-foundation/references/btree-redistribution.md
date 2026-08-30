<!-- capsule-v2 -->
# B-tree redistribution — why is greedy packing illegal without a repair pass, and which index-skew traps lurk in it?

**Source:** turso (MIT) @ main`f1800bb8c` (re-anchored from `def9a060` in the 21-commit drift wave); Codebase Memory `turso`. **Question:** How do I redistribute cells across siblings without producing a fanout violation or reading the wrong child pointer?

## balance_non_root: pack greedy, then REPAIR legality
**Path/Symbol:** `core/storage/btree.rs:balance_non_root` (:3245 verified @f1800bb8c), legality-repair comment (:3943-3962), overflow-cell adjustment (:3371-3393, formula :3383), two-pass safe update order (:4395-4428, SQLite quote block :4380-4403), root collapse trap (:4484-4528, defrag rule :4499-4503), post-balance validation harness (`post_balance_non_root_validation` :4641+).
**Signature:** collects all cells from up to three siblings plus their parent dividers into one flat CellArray, packs greedily left-to-right, then runs a second right-to-left pass moving cells back while moving more would improve balance.
**Data Shape:** divider construction differs by page type — interior dividers keep payload and repoint the left child; table-leaf dividers reuse the moved rowid; index-leaf dividers prepend the new page id to the stripped key. Page numbers are reassigned in sorted order so physical file order matches logical order.

### Decisive source
```text
// btree.rs:3943-3945 — the pass porters dismiss as an optimization:
// "This adjustment is more than an optimization.  The packing above might
//  be so out of balance as to be illegal. For example, the right-most
//  sibling might be completely empty. This adjustment is not optional."
```

Two more subtleties live here:
- **OVERFLOW CELL ADJUSTMENT** (:3371-3393): drop_cell() physically shifts cell-pointer slots left while insert_into_cell() stores overflow cells virtually. Consequence, verbatim: "'3' is actually physically located at index '2'. So IF the parent has an overflow cell, we need to subtract 1 to get the actual rightmost divider cell idx to physically read from" (formula :3383 `first_cell_divider + sibling_pointer - parent_contents.overflow_cells.len()`). Miss this and sibling loads read the wrong child pointer after InteriorNodeReplacement.
- **Two-pass safe update order** (:4395-4428, SQLite quote block :4380-4403): downward then upward pass with a `done[]` skip mask; when cells move left, don't update the target page until the left-hand sibling has been updated — mid-redistribution reads would see rewritten bytes.

Root collapse has its own trap: "It is critical that the child page be defragmented before being copied into the parent, because if the parent is page 1 then it will [be] smaller than the child due to the database header" (:4498-4503).

**Flow:** gather → greedy pack → right-to-left legality repair → update left-before-target → rebuild dividers per page type.
**Invariant:** encode "which states are illegal" as explicit post-passes with comments saying so, and document virtual-vs-physical index skew wherever code converts between them.
**Probe:** debug builds run `post_balance_non_root_validation` (:4641+): snapshot every cell before redistribution, verify byte-exact survival, no self/parent-pointing children, every new page reachable from a divider or rightmost pointer. Property tests prop_insertions_preserve_exact_cell_bytes / prop_defragment_fast_matches_full (:14064/:14263); fuzz drivers take a SEED env for reproducibility.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "turso", query: "balance_non_root CellArray divider", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the mandatory legality-repair pass and the overflow-cell index adjustment verbatim (the #1 wrong-port hazard); adapt packing heuristics freely; omit root-collapse handling if you never shrink depth. Coverage caveat: none material.
