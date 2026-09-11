<!-- capsule-v2 -->
# JSON duplicate keys — what happens when `{"a":1,"a":2}` is validated?

**Source:** pydantic-core MIT `main@383eb95a19433754c0cecf7025b50c26b6d97a36`; Codebase Memory `pydantic-core`. **Question:** Where must a port dedupe duplicate JSON object keys, and with which order semantics?

## jiter keeps duplicates; field lookup last-wins for free, kwargs conversion dedups explicitly (last occurrence wins, first-seen order kept)
**Path/Symbol:** `src/input/input_json.rs:JsonValue::as_kwargs` (:62-92), FIXME at validate_iter (:288), catch_duplicate_keys:false in JsonValidator Any-path (`src/validators/json.rs:76`); JsonObject is Vec-backed (:573-598).
**Signature:** `fn as_kwargs(&self, py: Python<'py>) -> Option<Bound<'py, PyDict>>`.
**Data Shape:** JsonObject = Vec<(Arc<str>, JsonValue)> preserving document order including duplicates.

### Decisive source
```rust
// deduplicate keys before creating objects to avoid wasted work
// jiter doesn't deduplicate keys, so duplicate keys in JSON will appear multiple times
// in the slice. We iterate backwards to keep only the last value for each key while preserving order
let unique_indices_reversed = { ... for (i, (k, _)) in object.as_slice().iter().enumerate().rev() {
    if seen.insert(k) { unique.push(i); } } ... };
```

**Flow:** two divergent consumers of the SAME duplicate-bearing slice: (1) LookupKey field access scans and naturally returns the LAST match — probe P8 executed live: `SchemaValidator(typed_dict{a:int}).validate_json('{"a": 1, "a": 2}') == {'a': 2}`; (2) function-validator kwargs need a real dict, so as_kwargs walks backwards collecting first-seen indices, then emits them forward — last value per key, original key order. Extra/iterate paths still YIELD duplicates (FIXMEs admit it at :92 comment block and :288) so extra='allow' models can observe both.
**Invariant:** Last-wins is the semantic everywhere; only ORDER differs by consumer (field lookup orderless; kwargs preserves document position of the key's FIRST appearance). A port that dedupes eagerly inside the parser changes observable extra-handling behavior; upstream deliberately does not.
**Probe:** P8 above (executed live); source pins byte-checked this pass. No dedicated upstream test file found for as_kwargs dedup ordering (search_graph "deduplicate keys before creating objects" → impl + FIXMEs only) — recorded caveat.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pydantic-core", query: "as_kwargs deduplicate keys backwards last", limit: 5 });
// live: five as_kwargs impls tie on rank (StringMapping/Input/Bound/JsonValue :62-92/str); the JsonValue impl carries the dedup body — open by qn, not rank
```

## Verdict
Adopt last-wins + lazy dedup split; adapt the backward-scan to your container; do NOT move dedup into parsing. Caveat: no upstream direct test pins kwargs ordering — treat the source excerpt as the contract. Coverage: input_json.rs no_recorded_issue @ gen 2026-08-25T20:09:30Z.
