<!-- capsule-v2 -->
# Type-name remapping — how do non-reserved keywords become valid type references (`type Foo<in in> = {}` needs `in` as a NAME) without corrupting the token stream?

**Source:** Biome MIT `main@6cd32636f463551b8dfe46aeefb1191d437b4694`; Codebase Memory `biome`. **Question:** When parsing type names, which keywords are remapped to identifiers, and what reserved set must never be?

## parse_ts_name + is_reserved_type_name
**Path/Symbol:** `crates/biome_js_parser/src/syntax/typescript/types.rs:parse_ts_name` (:965-982), `is_reserved_type_name` (:154-170), `is_reserved_module_name` (:172-174); dispatch guard in `parse_ts_non_array_type` (:919-943).
**Signature:** `fn parse_ts_name(p: &mut JsParser) -> ParsedSyntax` — dotted chain `JS_REFERENCE_IDENTIFIER (.` `parse_name` → `TS_QUALIFIED_NAME)*`.
**Data Shape:** Predefined-type keyword → fixed kind mapping happens ONLY when NOT followed by `.`; anything else falls to reference/qualified-name parsing.

### Decisive source
```rust
let mut left = if p.cur().is_non_contextual_keyword() && !p.cur().is_future_reserved_keyword() {
    let m = p.start();
    p.bump_remap(T![ident]);   // 'type', 'keyof', 'in' … legal as type NAMES here
    Present(m.complete(p, JS_REFERENCE_IDENTIFIER))
} else {
    parse_reference_identifier(p)
};
while p.at(T![.]) { /* … TS_QUALIFIED_NAME … */ }
```
```rust
// predefined-type shortcut only when not qualified:
if !p.nth_at(1, T![.]) {
    let mapping = match p.cur() {
        T![any] => Some(TS_ANY_TYPE), T![unknown] => Some(TS_UNKNOWN_TYPE),
        T![number] => Some(TS_NUMBER_TYPE), T![object] => Some(TS_NON_PRIMITIVE_TYPE),
        T![boolean] => Some(TS_BOOLEAN_TYPE), /* bigint/string/symbol/undefined/never */ … };
}
```

**Flow:** non-contextual, non-future-reserved keywords are re-tagged as plain idents so qualified names like `A.B.C` and keyword names parse uniformly; the predefined types (`any`, `string`, …) are matched to dedicated kind only when a `.` does NOT follow — `string.x` must stay a (bogus) reference, never `TS_STRING_TYPE` + junk.
**Invariant:** `bump_remap(T![ident])` changes only the emitted event's kind, not lexer state — safe precisely because type-name position has no other reading for those tokens. The reserved list (`string|null|number|object|any|unknown|boolean|bigint|symbol|void|never|undefined`) is used by *declaration* sites (e.g. type-alias name validation) while this mapping is used by *reference* sites — conflating them breaks `type string = number` diagnostics.
**Probe:** `crates/biome_js_parser/tests/js_test_suite/ok/ts_reference_type.ts` (`type E = D.c.b.a;`) plus modifier-error tests using escaped keyword names (`type Foo<i\u006E T>` in error/type_parameter_modifier.ts).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "biome", query: "parse_ts_name bump_remap qualified name reserved type", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt remap-on-event + dot-guarded predefined mapping; adapt keyword sets to host language; omit nothing portable.
