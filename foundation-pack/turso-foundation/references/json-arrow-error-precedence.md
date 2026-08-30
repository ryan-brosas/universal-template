<!-- capsule-v2 -->
# JSON arrow-operator error precedence — why must the document parse before the path?

**Source:** turso (Limbo) MIT `main@1654d1587`; Codebase Memory project `turso`. **Question:** When both the JSON document and the path are malformed, which error must `->` / `->>` report?

## Document-first parsing mirrors SQLite's jsonExtractFunc
**Path/Symbol:** `core/json/mod.rs`: `json_arrow_extract` (:487, reorder at :496-497), `json_arrow_shift_extract` (:515, reorder at :524-525); path parser entry `core/json/path.rs::json_path` (:80); commit `53e2bf4e4` "report malformed JSON before bad paths in -> and ->>" with upstream citation json502.test 2.3.
**Signature:** both fns: `(value: impl AsValueRef, path: impl AsValueRef, json_cache: &JsonCacheCell) -> Result<Value>`.
**Data Shape:** NULL document short-circuits to SQL NULL BEFORE any parsing (both fns :492-494/:520-522) — the only input that skips validation.

### Decisive source
```rust
// core/json/mod.rs:496-497 — conversion hoisted ABOVE path parsing:
//   let make_jsonb_fn = curry_convert_dbtype_to_jsonb(Conv::Strict);
//   let mut json = json_cache.get_or_insert_with(value, make_jsonb_fn)?;   // ← "malformed JSON" wins
//   if let Some(path) = json_path_from_db_value(&path, false)? {           // ← bad paths second
// Pre-fix the two lines were swapped inside the if-block, so
//   SELECT '{a:null,{"h":[1]}:true}' -> '$h[#-1]'
// reported a PATH error instead of SQLite's "malformed JSON".
```

**Flow:** strict-mode conversion of the document argument (which validates JSON text and rejects garbage) executes first through the cache cell; only a successfully converted document reaches path interpretation (`json_path_from_db_value(..., false)` — non-strict so bare labels become quoted keys); any path error surfaces after the document is known-good.
**Invariant:** error precedence is part of wire compatibility: an expression with TWO faults must fail with the DOCUMENT fault. The same hoist applies identically in both operators — keep them in lockstep or `->` and `->>` disagree on identical inputs.
**Probe:** from repo root: `grep -n -A3 'let make_jsonb_fn = curry_convert_dbtype_to_jsonb(Conv::Strict);' core/json/mod.rs | grep -c 'json_path_from_db_value'` → 4 (each operator shows cache-line directly above its path line, ×2 orderings ×2 operators); upstream blessing: `grep -c 'json502' sqlite/conformance/upstream/all.test` → 1 at line 351 marked pass.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "turso", query: "json_arrow_extract", limit: 3 });
```
(resolves the fn node in core/json/mod.rs at this pin)

## Verdict
Adopt validate-document-first ordering for every dual-argument JSON accessor; adapt error taxonomy to your host; omit the strict/non-strict path duality if your grammar has no bare-label shorthand. Coverage caveat: none material.
