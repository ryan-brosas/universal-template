<!-- capsule-v2 -->
# Import-type grammar — how does `typeof import("m", { with: … }).C<T>` assemble qualifier, arguments, and assertion block in one pass?

**Source:** Biome MIT `main@6cd32636f463551b8dfe46aeefb1191d437b4694`; Codebase Memory `biome`. **Question:** What is the fixed ordering of `import(...)` parts in type position, and which error-recovery shapes (trailing comma, missing `with`) does it pin?

## parse_ts_import_type family
**Path/Symbol:** `crates/biome_js_parser/src/syntax/typescript/types.rs:parse_ts_import_type` (:1156-1178), `parse_ts_import_type_arguments` (:1730-1754), `parse_ts_import_type_assertion(_block)` (:1674-1728).
**Signature:** `fn parse_ts_import_type(p: &mut JsParser, context: TypeContext) -> ParsedSyntax` — requires `import` or optional `typeof import`.
**Data Shape:** `TS_IMPORT_TYPE` = [`typeof`] `import` + `TS_IMPORT_TYPE_ARGUMENTS` + optional `TS_IMPORT_TYPE_QUALIFIER` (`.name`) + optional type arguments `<T>`; assertion block reuses module-side `ImportAssertionList`.

### Decisive source
```rust
let m = p.start();
p.eat(T![typeof]);          // optional
p.expect(T![import]);
parse_ts_import_type_arguments(p, context).or_add_diagnostic(p, expected_ts_import_type_with_arguments);
if p.at(T![.]) {            // qualifier AFTER the call-like parens
    let qualifier = p.start();
    p.bump(T![.]);
    parse_ts_name(p).or_add_diagnostic(p, expected_identifier);
    qualifier.complete(p, TS_IMPORT_TYPE_QUALIFIER);
}
parse_ts_type_arguments(p, context).ok();   // generic args LAST
```
Arguments/errors:
```rust
if p.at(T![,]) {
    if p.nth_at(1, T![')']) { p.error("ts import type may not have a trailing comma"…); }
    p.bump(T![,]);
    parse_ts_import_type_assertion_block(p).ok();   // `, { with: {…} }`
}
```

**Flow:** `(` → type (the module specifier) → optional `, {assert|with: {...}}` block → `)` → optional `.qualifier` → optional `<type args>`. Assertion keywords accepted as legacy `assert` or current `with`; an empty `{}` block errors "Missing import type assertion keyword 'with'".
**Invariant:** The argument list is NOT a general expression call — exactly one type plus an optional options object; a trailing comma is an error *but still consumed* so recovery stays local. Qualifier comes after the parenthesized form because `import("m").C` is the only legal shape — reversing the order breaks every real-world import type.
**Probe:** `crates/biome_js_parser/tests/js_test_suite/ok/ts_import_type.ts` (`typeof import("test", { with: { "resolution-mode": "require" } }).a.b.c.d.e.f`, `import("test")<string>`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "biome", query: "parse_ts_import_type qualifier assertion with resolution-mode", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the fixed four-part ordering and consume-on-error trailing-comma recovery; adapt kinds/option keys; omit message text.
