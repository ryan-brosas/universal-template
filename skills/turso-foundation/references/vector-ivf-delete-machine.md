<!-- capsule-v2 -->
# Vector-IVF delete machine — why must delete be paranoid where insert is blind, and what stats drift is accepted?

**Source:** turso (MIT) `main@1654d1587fab` (/mnt/hdd/utopia/inspo/turso); Codebase Memory `turso`. **Question:** What does a correct posting-list removal look like under async seeks, and which inconsistencies are tolerated after deletes?

## Eight-state machine: Found deletes in place, TryAdvance advances first, NotFound is corruption
**Path/Symbol:** `core/index_method/toy_vector_sparse_ivf.rs`: `VectorSparseInvertedIndexDeleteState` enum (:90-137), `delete` (:785-1044).
**Signature:** `fn delete(&mut self, values: &[Register]) -> Result<IOResult<()>>` with `values = [old_sparse_vector_blob, rowid_i64]` — deletion needs the OLD vector, so UPDATE = delete(old)+insert(new).
**Data Shape:** same key shapes as insert. Extra state vs insert: `NextInverted` (advance arm) — insert has no counterpart.

### Decisive source
```rust
// toy_vector_sparse_ivf.rs:886-910 — the three-arm seek ladder (verbatim):
match result {
    SeekResult::Found => { /* -> DeleteInverted */ }
    SeekResult::TryAdvance => {
        self.delete_state = VectorSparseInvertedIndexDeleteState::NextInverted { .. };
    }
    SeekResult::NotFound => {
        return Err(LimboError::Corrupt("inverted index corrupted".to_string()));
    }
}
// :912-927 NextInverted — advance then trust positioning:
return_if_io!(cursor.next());
if !cursor.has_record() {
    return Err(LimboError::Corrupt("inverted index corrupted".to_string()));
}
```

**Flow:** identical Init/Prepare preamble as insert → SeekInverted three-arm ladder → DeleteInverted (`cursor.delete()`) → SeekStats `(position)`: Found ⇒ ReadStats builds `(cnt−1, min, max)` (:983-1020); NotFound|TryAdvance ⇒ **Corrupt "stats index corrupted: can't find component row"** (:976-980) → UpdateStats re-inserts stats row → Prepare idx+1.
**Invariant:** delete MUST find its exact row — a missing posting means index/table divergence, so Corrupt is the honest failure; this is the mirror of insert's ignored seek result. On TryAdvance the code advances once and deletes whatever record it lands on WITHOUT re-verifying content — sound only because `eq_only:true` GE semantics guarantee the next record IS the sought key when it exists. Stats drift is accepted by design: cnt decrements (possibly to 0, row never removed) but min/max are NEVER re-shrunk — stale-wide bounds keep the query-side pruning conservative (it may over-scan candidates, never miss true ones).
**Probe:** executed at HEAD: `test_vector_sparse_ivf_update` (tests/integration/index_method/mod.rs:245-325) exercises delete(old)+insert(new) after an UPDATE and asserts the reader flips from empty to exact `(rowid 1, distance 0.0)`. Grep anchors verified byte-exact: TryAdvance arm :896; Corrupt strings :907/:920/:978; `component.cnt - 1` :1000.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "turso", query: "VectorSparseInvertedIndexDeleteState NextInverted DeleteInverted", limit: 10 });
```
resolves the enum :90-137 and `delete` :785-1044 line-exact.

## Verdict
Adopt the Found/TryAdvance/NotFound triage with Corrupt on missing postings, and the advance-once-trust-position rule WITH the eq_only precondition that makes it sound. Adopt min/max non-shrinking as documented conservatism — recomputing them would need a full posting scan per delete. Adapt the update path if your engine hands old+new values in one call. Omit nothing else; the paranoia is load-bearing. Coverage: no_recorded_issue.
