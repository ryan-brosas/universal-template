<!-- capsule-v2 -->
# Import clause dispatch ladder — how do you parse bare/namespace/named/default/combined imports when `type`, `defer`, and `source` are all contextual?

**Source:** Biome MIT `main@6cd32636f463551b8dfe46aeefb1191d437b4694`; Codebase Memory `biome`. **Question:** After `import`, one dispatch must route `from "m"` (bare), `* as ns`, `{a, b}`, `type X from`, `defer * as ns`, `source x from`, `x, {y}` (combined), plus the invalid-source recovery path — in what order, and what does each arm consume?

## parse_import_clause + *_rest family
**Path/Symbol:** `crates/biome_js_parser/src/syntax/module.rs:parse_import_or_import_equals_declaration` (:212-267), `parse_import_clause` (:269-330), `parse_import_default_clauses_rest` (:334-362), bare/namespace/named rest fns (:364-389).
**Signature:** `fn parse_import_clause(p: &mut JsParser) -> ParsedSyntax`; rest-fns take `(p, m: Marker, is_typed: bool) -> CompletedMarker`.
**Data Shape:** Clause kinds: `JS_IMPORT_BARE_CLAUSE`, `JS_IMPORT_DEFAULT_CLAUSE`, `JS_IMPORT_NAMESPACE_CLAUSE`, `JS_IMPORT_NAMED_CLAUSE`, `JS_IMPORT_COMBINED_CLAUSE` (default + named/namespace in one statement). The marker `m` is started *before* typed-keyword lookahead so all arms complete the same node.

### Decisive source
```rust
// top of parse_import_clause — bare import needs NO marker:
if p.at(JS_STRING_LITERAL) || p.cur().is_metavariable() && !p.nth_at(1, T![from]) {
    return parse_import_bare_clause(p);
}
let pos = p.source().position();     // for the no-consumption debug_assert
let m = p.start();
// ... is_typed ladder (see references/module-typed-specifier-ladder.md) ...
match p.cur() {
    T![*] => parse_import_namespace_clause_rest(p, m),
    T!['{'] => parse_import_named_clause_rest(p, m),
    T![defer] if matches!(p.nth(1), T![*]) => parse_import_namespace_clause_rest(p, m),
    T![source] => { /* phase-import: eat source; else default-binding named `source` */ }
    _ if is_at_identifier_binding(p) => parse_default_import_specifier(p, m, is_typed),
    _ => { debug_assert_eq!(pos, p.source().position()); m.abandon(p); return Absent; }
}

// default-rest: after the binding, `, {…}` or `, *…` upgrades to COMBINED — but
// a type-only import can't have both:
T![,] | T!['{'] | T![*] => {
    p.expect(T![,]); /* namespace or named */
    if is_typed { p.error("A type-only import can specify a default import or named bindings, but not both."); }
    JS_IMPORT_COMBINED_CLAUSE
}
```

**Flow:** string → bare (no marker started) → else start marker → typed lookahead (may eat `type`) → keyword/binding dispatch → each rest fn: specifiers, `expect(from)`, module source, attributes, complete. Statement wrapper (:221-264) sets `duplicate_binding_parent = Some("import")` before the clause and clears `name_map` after — import bindings are checked as one declaration group.
**Invariant:** The Absent arm must leave position untouched (`debug_assert_eq!(pos, …)`) because callers treat Absent as "not an import clause at all" and produce their own diagnostic; any arm that consumed tokens must instead recover internally. The invalid-`source` recovery (:233-246) bumps to `;` deliberately — a broken import header cannot be reinterpreted. Bare-clause detection happens before the marker so an absent clause never leaks an empty node.
**Probe:** `crates/biome_js_parser/tests/js_test_suite/ok/module.js` (all five clause kinds incl. `import type` forms) and `ok/import_attribute.js`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "biome", query: "parse_import_clause parse_import_default_clauses_rest JS_IMPORT_COMBINED_CLAUSE", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt marker-first dispatch with a strict no-consumption Absent contract for multi-arm productions; adapt the contextual keyword set; omit combined-clause handling if your module grammar lacks default+named fusion. Coverage caveat: full-mode index, metadata_match.
