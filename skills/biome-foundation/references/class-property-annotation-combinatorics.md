<!-- capsule-v2 -->
# Optional/definite property annotation — how do `?` and `!` interact with abstract, declare, and ambient context without producing stacked diagnostics?

**Source:** Biome MIT `main@6cd32636f463551b8dfe46aeefb1191d437b4694`; Codebase Memory `biome`. **Question:** A class property can be optional (`?`), definite (`!`), both-written (`a?!: T`), annotated or not, inside ambient contexts — what single function owns this combinatorics?

## parse_ts_property_annotation + optional_member_token
**Path/Symbol:** `crates/biome_js_parser/src/syntax/class.rs:parse_ts_property_annotation` (:1106-1199), `optional_member_token` (:1202-1220), consumed by `parse_property_class_member_body` (:995-1077).
**Signature:** `fn parse_ts_property_annotation(p: &mut JsParser, modifiers: &ClassMemberModifiers) -> ParsedSyntax`; `fn optional_member_token(p) -> Result<Option<TextRange>, TextRange>` (Ok(range) = valid TS `?`, Err(range) = `?` seen but illegal).
**Data Shape:** Produces `TS_OPTIONAL_PROPERTY_ANNOTATION`, `TS_DEFINITE_PROPERTY_ANNOTATION`, or `JS_BOGUS` (both markers present). The Result-vs-Option split encodes *emitted vs pending* errors so callers don't re-report.

### Decisive source
```rust
let optional_range = match optional_member_token(p) {
    Ok(optional_range) => optional_range,
    Err(optional_range) => { valid = false; Some(optional_range) }  // error already emitted
};
// ... definite `!` branch checks in order:
if TypeScript.is_unsupported(p) { /* ts-only error */ }
else if modifiers.has(Abstract) { /* '!' cannot appear on abstract */ }
else if modifiers.has(Declare) || p.state().in_ambient_context() { /* not in ambient */ }

match (optional_range, definite_range) {
    (Some(_), None) => parse_ts_type_annotation(...); TS_OPTIONAL_PROPERTY_ANNOTATION
    (None, Some(_)) => { annotation REQUIRED here: "Properties with definite assignment
                         assertions must also have type annotations." ; DEFINITE }
    (Some(_), Some(_)) => { parse annotation; "cannot be both optional and definite" (two details);
                            JS_BOGUS }
}
```

**Flow:** no `?`/`!` → plain type annotation (mandatory, error if absent) → else consume `?` (ts-gated) and/or `!` with per-context legality → dispatch on which pair appeared; definite-without-annotation gets its own dedicated diagnostic.
**Invariant:** Exactly one owner per diagnostic: `optional_member_token` reports ts-illegality itself and signals via `Err`, while the caller tracks a local `valid` flag and demotes the completed annotation to bogus at the end — so the node is marked invalid exactly once regardless of how many contextual errors fired. Post-completion initializer cross-checks (:1035-1074) reuse the same one-error discipline: abstract+initializer errors, declare/ambient requires readonly, readonly+annotation+initializer conflicts — each mutually exclusive branches. Method members share `optional_member_token` for `test?()` with the caller-side demotion pattern (`member.change_to_bogus` on `optional.is_err()`, :1333-1336), keeping one implementation for two call sites.
**Probe:** `crates/biome_js_parser/tests/js_test_suite/error/ts_abstract_property_cannot_be_definite.ts` and `error/ts_annotated_property_initializer_ambient_context.ts` pin the exact single-diagnostic outputs.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "biome", query: "parse_ts_property_annotation optional_member_token TS_DEFINITE_PROPERTY_ANNOTATION", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the Ok/Err range protocol + end-of-function bogus demotion for token-level feature flags with dialect gates; adapt the modifier interactions; omit the definite-assignment lane outside TS-like hosts. Coverage caveat: full-mode index, metadata_match.
