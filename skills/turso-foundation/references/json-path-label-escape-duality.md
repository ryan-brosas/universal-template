<!-- capsule-v2 -->
# JSON path-label escape duality — when is a stored key decoded before comparison?

**Source:** turso (Limbo) MIT `main@1654d1587`; Codebase Memory project `turso`. **Question:** How must stored object keys and path labels be normalized so `'{\"abc\":123}' ->> 'a\x62c'` finds the key, and which element type stores a label that contains backslashes?

## jsonLabelCompare mirror: decode only the side that carries escapes
**Path/Symbol:** `core/json/jsonb.rs`: `fn new_key_element_type` (:3578-3586), `fn compare` (:3598-3615), call sites :2879 (insert arm) and :3049 (set arm); shorthand rewrite `PathElement::Key(label, true)` for non-`$` text paths in `core/json/mod.rs::json_path_from_db_value` (:771, quoted flag at :791, pinned by `test_json_path_from_db_value_named_non_strict` :1770); unescape helper `unescape_string` (jsonb.rs:4114).
**Signature:** `fn new_key_element_type(path_key: &str, is_quoted: bool) -> ElementType`; `fn compare(key: (&str, ElementType), path_key: (&str, bool)) -> bool`.
**Data Shape:** ElementType of a created key ∈ {TEXT5 (quoted + has `\`), TEXTRAW (quoted, no escapes), TEXT (unquoted; its serializer re-escapes)}; compare accepts only TEXT/TEXTJ/TEXT5/TEXTRAW keys.

### Decisive source
```rust
// core/json/jsonb.rs:3607-3615 — the 2×2 matrix IS the contract:
let key_is_raw = matches!(element_type, ElementType::TEXT | ElementType::TEXTRAW);
let path_is_raw = !is_quoted || !path_key.contains('\\');
match (key_is_raw, path_is_raw) {
    (true, true)  => key == path_key,
    (true, false) => key == unescape_string(path_key),
    (false, true) => unescape_string(key) == path_key,
    (false, false)=> unescape_string(key) == unescape_string(path_key),
}
```

**Flow:** `-> 'label'` shorthand parses as if written `$."label"` (quoted=true) → lookup walks elements calling `compare` per candidate key, decoding exactly the escape-carrying sides → creation via json_set/insert picks the storage type from `new_key_element_type`: quoted-with-backslash ⇒ TEXT5 so escapes SURVIVE re-rendering (`json_set('{}', '$."\"Key"', 1)` must emit `{"\"Key":1}`, not double-escaped bytes); unquoted keeps legacy TEXT so json_patch output bytes stay stable.
**Invariant:** never store an escape-bearing quoted label as TEXTRAW (the old bug: serialization re-escaped it) and never compare raw-vs-decoded asymmetrically (the old ad-hoc mix broke whenever either side held a backslash). A side with no escapes compares as raw bytes.
**Probe:** from repo root: `grep -c "if is_quoted && path_key.contains('\\\\\\\\')" core/json/jsonb.rs` → 1 (TEXT5 branch); conformance proof: `grep -c '3\.2' sqlite/conformance/upstream/json502.test` → 1 with body `'{"abc":123}' ->> 'a\x62c'` → 123 (upstream-blessed, `all.test:351` shows `json502 pass`). Runner: `cargo test -p turso_core --features json --lib -- json::` → 175 passed at this pin.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "turso", query: "new_key_element_type compare unescape_string", limit: 4 });
```
(live-resolved rank hits on all three symbols line-exact at this pin)

## Verdict
Adopt the two-flag raw×raw compare matrix and the TEXT5-for-escaped-labels rule verbatim; adapt element-type names to your JSONB dialect; omit TEXTJ handling unless you accept JSON-native key syntax. Coverage caveat: none material.
