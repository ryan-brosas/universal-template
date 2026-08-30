<!-- capsule-v2 -->
# MVCC visibility predicates — what exact rules decide "can transaction T see version V", including the Hekaton paper's own typo fix?

**Source:** turso MIT `main@def9a060`; Codebase Memory `turso`. **Question:** What is the complete begin/end visibility truth table a porter must reproduce?

## is_begin_visible && is_end_visible with conservative fall-through on unknowns
**Path/Symbol:** `core/mvcc/database/mod.rs:9900+` (`is_visible_to`), begin arms :10070+, end arms incl. Hekaton Case-1/Case-2 excerpt :2905-2935, typo fix + citation :10171-10173 (`Source: https://avi.im/blag/2023/hekaton-paper-typo/`), monotonicity assert :9935 ("begin_ts and committed end_ts cannot be equal: txn timestamps are strictly monotonic").
**Signature:** `fn is_visible_to(&self, txs, finalized_tx_states, reader_tx, rv: &RowVersion) -> bool` = `is_begin_visible && is_end_visible`.
**Data Shape:** each arm resolves PackedTs → Timestamp (compare numerically) or TxID (state lookup: live map → finality cache → conservative default).

### Decisive source
```text
// mod.rs:10070-10240 region — the two-predicate reduction:
//   is_begin_visible: creator committed at ts ≤ reader.begin_ts,
//     OR creator IS the reader (own writes visible), OR speculative
//     registration against a Preparing creator.
//   is_end_visible: undeleted, deleter aborted, deleter IS the reader
//     (Hekaton TYPO FIX — the paper omits this own-txid case:
//      mod.rs:10171-10173), or speculative-ignore of a Preparing deleter.
// Unknown TxIDs degrade CONSERVATIVELY: begin invisible, end visible.
```
The own-txid end case matters because a transaction must still see rows it deleted itself mid-transaction; Hekaton's published table misses it and turso's comment links the community correction. Speculative arms are where commit dependencies get registered (see dependency capsule) — visibility and dependency bookkeeping are one mechanism, not two.

**Flow:** read → locate chain (MVCC map) → reverse scan → first version passing both predicates wins | none ⇒ row invisible.
**Invariant:** strictly monotonic timestamps make equality impossible between distinct commits — asserts encode this as corruption detection; conservative defaults always fail toward invisibility/conflict, never visibility.
**Probe:** tests.rs:6678-6815 hand-built tables vs Hekaton Tables 1&2; hermitage G1a/G1b/OTV end-to-end.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "turso", query: "is_visible_to is_begin_visible is_end_visible", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the full truth table INCLUDING the typo fix; adapt state lookup to your maps. The conservative-default direction is not a free choice — flipping it breaks snapshot isolation silently.
