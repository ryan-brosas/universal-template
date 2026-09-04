<!-- capsule-v2 -->
# B-tree covers-chain gate — when may a scan skip the MVCC version store and read a key straight from the B-tree?

**Source:** turso MIT `main@def9a0601b8e`; Codebase Memory `turso`. **Question:** Under passive checkpointing a row can live in BOTH the SkipMap version store and the materialized B-tree — what exact predicate decides which copy a reader sees, and why does it flip off during checkpoints?

## A chain is B-tree-covered only when the binding is readable, no checkpoint runs, and the chain reduces to one committed current below checkpoint coverage
**Path/Symbol:** `core/mvcc/database/mod.rs`: `btree_covers_chain_for_tx` (:5572-5589), `chain_is_write_buffer_for` (:5536-5565), `query_btree_version_is_valid` (:5627), `find_last_visible_version` (:5686), consumers `MvccLazyCursor::query_btree_version_is_valid` (`core/mvcc/cursor.rs`:805) and scan advance paths.
**Signature:** `btree_covers_chain_for_tx(tx, table_id, versions) -> bool`; early-false ladder: `experimental_mvcc_passive_checkpoint` → `checkpoint_in_progress.load(Acquire)` → `!is_btree_readable_at(table_id, tx.begin_ts, tx.read_mark)` → then the per-chain shape test.
**Data Shape:** "write-buffer" shape (⇒ NOT covered, must merge versions): empty; len≠1; begin not a Timestamp; end set; invisible to tx; `begin_ts > durable_txid_max`; `materialized_at == ORIGIN`; or `reader_mark < materialized_at`. Only `versions == [one committed current, timestamped, visible, ≤ ckpt_max, materialized at/below the reader's mark]` falls through.

### Decisive source
```rust
// mod.rs:5566-5571 — the mode split:
//   // Passive keeps SkipMap cover for all chains (table/index views can disagree
//   // under concurrent Passive). Truncate may fall through for sole materialized
//   // currents when no checkpoint is in progress.
// mod.rs:5549-5552 — conservative over-approximation of write-buffer membership:
//   // Passive may stamp materialized_at during write-out before publish.
//   if begin_ts > ckpt_max { return true; }
// mod.rs:5633-5638 — absent from the store means the B-tree is authoritative:
//   let Some(versions) = self.rows.get(&row_id_full) else {
//       // No MVCC version -> B-tree is valid
//       return true;
// cursor.rs:602/:805 — the cursor funnels every B-tree row through this predicate.
```
The same predicate drives three call sites with one meaning: point reads (`query_btree_version_is_valid`, :5627), table-scan skip (`find_last_visible_version` returns None ⇒ cursor uses the B-tree cell, :5686), and index shadowing (`index_chain_invalidates_btree` :5589 region — covered chain ⇒ no invalidation possible). Scan-path reads of an already-resolved chain go through `read_visible_from_versions`/`read_visible_into_record` (:5391/:5414), which serialize into the caller's record instead of cloning a `Row`.

**Flow:** reader asks about key K → if no SkipMap entry, B-tree wins outright → else run the early-false ladder → covered ⇒ serve/validate from B-tree and skip merging → not covered ⇒ newest-first visibility scan decides, with the B-tree treated as valid only when the top version says so.

**Invariant:** under PASSIVE checkpointing the SkipMap NEVER yields cover (mode flag short-circuits first); during any in-progress checkpoint cover is withdrawn globally (`Acquire` load) so collection cannot race a reader's fallback; otherwise cover requires BOTH clocks already pinned by `is_btree_readable_at` AND single-current chain shape. When in doubt the code merges versions — false negatives cost performance, false positives corrupt reads. The doc comment on `compute_min_reader_mark` (:9636-9641) gives the GC-side mirror: freshly materialized rows are reclaimable only once every Active/Preparing reader's mark reaches them.

**Probe:** `core/mvcc/database/tests.rs:7081` documents the authority contract: `query_btree_version_is_valid` evaluates the version chain ONLY for keys that exactly match a B-tree row — stepping over an MVCC-only key must not fire its side effects (`test_index_finger_no_spurious_dep_on_stepped_over_key`, :7093, pins zero spurious commit dependencies on stepped-over keys). The dual-gate lifecycle behind clause 3 is pinned by `mvcc_btree_read_dual_gate` (:1128).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "turso", query: "query_btree_version_is_valid btree_covers_chain_for_tx chain_is_write_buffer_for", limit: 6, fields: ["signature", "name", "file"] });
```
(graph resolves all four to `core/mvcc/database/mod.rs` / `cursor.rs`.)

## Verdict
Adopt the early-false ladder and the fail-closed direction verbatim; re-enabling cover for multi-version or uncommitted-tail chains reintroduces lost-update reads. Adapt the two mode flags to your checkpoint driver's vocabulary. Omit the Truncate-vs-Passive distinction if you ship a single checkpoint mode.
