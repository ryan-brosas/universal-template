<!-- capsule-v2 -->
# Declaration-clause gate — how does `export`/`declare` decide between a dozen declaration forms with pure token probes, and why does `type X = …` need line-break and `{`-guards?

**Source:** Biome MIT `main@6cd32636f463551b8dfe46aeefb1191d437b4694`; Codebase Memory `biome`. **Question:** What is the complete lookahead predicate that recognizes "this next statement is a declaration clause", and how do decorators dispatch inside it?

## is_nth_at_declaration_clause + parse_declaration_clause
**Path/Symbol:** `crates/biome_js_parser/src/syntax/auxiliary.rs:is_nth_at_declaration_clause` (:39-76), `parse_declaration_clause` (:78-161), `parse_variable_declaration_clause` (:29-37).
**Signature:** `fn is_nth_at_declaration_clause(p: &mut JsParser, n: usize) -> bool` — pure multi-token probe, no consumption.
**Data Shape:** Dispatch table over cur(): function/@/class|abstract/const(enum?)/var/enum/import/async/type/interface/let/namespace|global|module.

### Decisive source
```rust
if p.has_nth_preceding_line_break(n + 1) {
    return false;                       // ASI: 'type'/'interface' must sit on the SAME line
}
if p.nth_at(n, T![type]) && !p.nth_at(n + 1, T![*]) && !p.nth_at(n + 1, T!['{']) {
    return true;                        // excludes `type *…` (import type *) and `{type …}` blocks
}
```
Decorator arm:
```rust
T![@] => {
    let decorator_list = parse_decorators(p);
    match p.cur() {
        T![class] | T![abstract] if !p.state().in_ambient_context() => {
            parse_class_declaration(p, decorator_list, StatementContext::StatementList)
        }
        _ => {  // @decorator export let a; — illegal placement
            decorator_list.add_diagnostic_if_present(p, decorators_not_allowed)
                .map(|mut marker| { marker.change_kind(p, JS_BOGUS_STATEMENT); marker });
            parse_declaration_clause(p, stmt_start_pos)   // re-dispatch WITHOUT the decorators
        }
    }
}
```

**Flow:** probe answers "declaration clause?" for export/declare bodies → dispatcher maps each keyword to its declaration parser; `const enum` forks before variable clause; decorators parse once then either feed class or demote-to-bogus + re-dispatch. The variable clause wraps its declaration in a precede-marker with `semi()` so `export let a;` owns its semicolon.
**Invariant:** The line-break guard ordering matters: it runs BEFORE the `type` check but AFTER cheap kind checks — moving it earlier breaks `const\nenum`, later breaks ASI on `export type`. Decorators are consumed exactly once: the re-dispatch after bogus-demoting them must not see `@` again (it can't — they were bumped). Ambient context suppresses decorated classes (`declare @dec class` is invalid).
**Probe:** `crates/biome_js_parser/tests/js_test_suite/error/decorator_export_class_clause.js` (decorator before non-class exports) / `ok/decorator_export_class_clause.js` and `ok/export_variable_clause.js` (+error variant pinning `export const b;`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "biome", query: "is_nth_at_declaration_clause parse_declaration_clause export declare", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the single predicate + keyword-table dispatch shape for clause-position parsing; adapt to host declaration set; omit TS-only arms when porting to plain JS hosts.
