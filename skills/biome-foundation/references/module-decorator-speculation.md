<!-- capsule-v2 -->
# Module-level decorator speculation — how do you attach decorators to the right top-level declaration when only `class`/`abstract class`/`export class` can carry them?

**Source:** Biome MIT `main@6cd32636f463551b8dfe46aeefb1191d437b4694`; Codebase Memory `biome`. **Question:** Decorators are parsed greedily at statement level, but `@dec function f(){}` is illegal — how does the parser both route legal cases and recover illegal ones without losing or duplicating diagnostics?

## parse_module_item @ arm + parse_export_default_clause @ arm
**Path/Symbol:** `crates/biome_js_parser/src/syntax/module.rs:parse_module_item` (:117-210), export-default decorator ladder (:1176-1230); demotion helper pattern shared with `parse_export`.
**Signature:** `fn parse_module_item(p: &mut JsParser) -> ParsedSyntax`; decorator list is a `ParsedSyntax` threaded as an argument into `parse_export(p, decorator_list)` / `parse_class_declaration(p, decorator_list, ctx)`.
**Data Shape:** `ParsedSyntax` of a completed `JS_DECORATOR_LIST` (possibly empty via `empty_decorator_list`) — passed *by value* down the ladder; on rejection it's converted with `.add_diagnostic_if_present(p, decorators_not_allowed).map(|m| m.change_kind(JS_BOGUS_STATEMENT))`.

### Decisive source
```rust
T![@] => {
    let decorator_list = parse_decorators(p);           // speculative: parsed before target known
    match p.cur() {
        T![export] if is_at_export_class_declaration(p) || is_at_export_default_class_declaration(p) =>
            parse_export(p, decorator_list),
        T![class] => parse_class_declaration(p, decorator_list, StatementContext::StatementList),
        T![abstract] if is_at_ts_abstract_class_declaration(p, LineBreak::DoCheck) => /* TS-gated */,
        _ => {  // @dec function / @dec let / @dec interface ...
            decorator_list.add_diagnostic_if_present(p, decorators_not_allowed)
                .map(|mut marker| { marker.change_kind(p, JS_BOGUS_STATEMENT); marker });
            parse_module_item(p)                        // re-dispatch AFTER consuming decorators
        }
    }
}
```

**Flow:** see `@` → parse the full decorator list → lookahead dispatch: class-carrying forms get the list threaded in (the declaration precedes its own marker with it: `decorator_list.precede(p)` inside `parse_class`), everything else demotes the list to bogus with one diagnostic and **recursively re-parses the module item** so the underlying statement still gets parsed normally.
**Invariant:** The decorator tokens are consumed exactly once — either attached to a declaration or folded into a bogus node — never abandoned; that's why the fallback recurses after demotion instead of rewinding. The same shape repeats inside `export default`: `@dec` + non-class falls through a per-keyword ladder (`function`, `async function`, `interface`, `enum`, else expression) each emitting its specific "decorators not allowed" error while preserving the default-expression path. Parameter decorators are separately feature-gated via `p.options().should_parse_parameter_decorators()` (`parse_parameter_decorators`, :2770-2784) — off means parse-then-bogus, not skip.
**Probe:** `crates/biome_js_parser/tests/js_test_suite/ok/decorator_export_top_level.js` (pins `@before.field @before @(() => decorator)()` chains incl. call-expression decorators) against `ok/decorator_class_not_top_level.js`-style error corpus for `if (a) { @dec class … }` rejection.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "biome", query: "parse_module_item decorator_list decorators_not_allowed", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt speculative-list parsing + consume-once demotion + recursive redispatch for prefix modifiers of uncertain legality; adapt the legal-carrier set; omit parameter-decorator gating if the host has no experimental-feature flags. Coverage caveat: full-mode index, metadata_match.
