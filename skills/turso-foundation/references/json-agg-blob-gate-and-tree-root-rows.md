<!-- capsule-v2 -->
# JSON aggregate blob rejection + json_tree root columns — which aggregates reject raw blobs, and what do root rows report?

**Source:** turso (Limbo) MIT `main@1654d1587`; Codebase Memory project `turso`. **Question:** Where must the "JSON cannot hold BLOB values" gate sit in group aggregates, and how are parent/path computed for json_tree rows rooted at a primitive?

## Aggregate-step blob gate + primitive-root row contract
**Path/Symbol:** `core/json/mod.rs`: `ensure_blob_arg_is_jsonb` (:316-323, made `pub(crate)` by the wave), existing scalar call sites :342/:362/:428/:905 (json_array/object/patch families); NEW aggregate-step sites `core/vdbe/execute.rs:7175` (JsonGroupObject value) and `:7226` (JsonGroupArray arg); vtab fixes `core/json/vtab.rs`: primitive-root `parent = None` (:424-435), `element_length` quoted-key arithmetic `key.len() + 3` vs bare `key.len() + 1` (:779-786); commits bd4735743 (blob gate, blesses json103) and 6ef02dfa8 (root row, blesses json502).
**Signature:** `fn ensure_blob_arg_is_jsonb(value: ValueRef) -> Result<()>` — bails CONSTRAINT error unless the blob passes `is_jsonb_blob` (:157).
**Data Shape:** aggregate payload register is a Blob accumulating JSONB frames; a NON-JSONB blob input previously flowed into text parsing and failed with unrelated messages ("Leading zero is not allowed" for x'303132').

### Decisive source
```rust
// core/vdbe/execute.rs:7172-7175 — gate BEFORE any conversion, in the AGGREGATE step
// (the scalar functions already had it — only the group variants were missing):
//   } else {
//       ensure_blob_arg_is_jsonb(value.as_value_ref())?;
//   }
//   let mut key_vec = convert_dbtype_to_raw_jsonb(arg, Conv::ToString)?;
```

Root-row rule: an IteratorState::Primitive describes ONLY the traversal root, and the root has no parent ⇒ emit SQL NULL even when json_tree was called with a non-root start path (:426-433). The path column trims the last element from the root path text; a quoted key contributes `dot + 2 quotes + key`, so under-counting leaked a dangling `."` into output.
**Invariant:** the same blob-rejection invariant holds at EVERY entry that converts user data into JSONB — add the gate at new entry points, don't rely on downstream parse failures. Root rows are parent-less regardless of where traversal started; path-trim length arithmetic must count syntax characters (quotes/dots), not just key bytes.
**Probe:** from repo root: `grep -c 'ensure_blob_arg_is_jsonb' core/vdbe/execute.rs` → 3 (1 import :151 + 2 agg sites :7175/:7226); `grep -c 'Key(key, true) => key.len() + 3' core/json/vtab.rs` → 1. Runners at this pin: `cargo test -p turso_core --features json --lib -- json::` → 175 passed; conformance census `grep -c 'json103\|json502' sqlite/conformance/upstream/all.test` → 2, both marked pass.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "turso", query: "ensure_blob_arg_is_jsonb JsonEachCursor", limit: 4 });
```
(resolves the mod.rs fn node line-exact at this pin)

## Verdict
Adopt up-front JSONB-blob validation in every aggregate step you port; adopt NULL-parent primitive roots and quote-aware trim lengths in any tree-walk table-valued function; omit the vtab plumbing if your engine exposes tree walks differently. Coverage caveat: none material.
