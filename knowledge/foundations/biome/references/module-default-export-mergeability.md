<!-- capsule-v2 -->
# Mergeable export-default items — how do you enforce "one default export per module" while letting TS overload sets and multiple default interfaces coexist?

**Source:** Biome MIT `main@6cd32636f463551b8dfe46aeefb1191d437b4694`; Codebase Memory `biome`. **Question:** What state tracks the module's existing default export, and which second defaults are legal instead of erroneous?

## ExportDefaultItem / ExportDefaultItemKind
**Path/Symbol:** `crates/biome_js_parser/src/syntax/module.rs:parse_export_default_clause` (:1167-1292), kind constructors (:1294-1371); state types `crates/biome_js_parser/src/state.rs:ExportDefaultItemKind.is_mergeable` (:40-42) + `JsParserState.default_item`.
**Signature:** `fn parse_export_default_clause(p: &mut JsParser) -> ParsedSyntax`; clause fns return `(ParsedSyntax, ExportDefaultItemKind)`.
**Data Shape:** `default_item: Option<ExportDefaultItem>` where the item carries `range` and `kind: ExportDefaultItemKind::{Expression, Declaration, ClassDeclaration, FunctionDeclaration, FunctionOverload, Interface}`. `is_mergeable` is true only for the FunctionOverload↔FunctionOverload pair; `is_interface` marks interfaces (never stored).

### Decisive source
```rust
clause.map(|mut clause| {
    if let Some(existing) = p.state().default_item.as_ref().filter(|_| p.is_module()) {
        if existing.kind.is_mergeable(&default_item_kind) {
            // overloads + implementation: OK, no check that they match
        } else {
            p.error(err_builder("Illegal duplicate default export declarations", ...)
                .with_detail(clause.range(p), "multiple default exports are erroneous")
                .with_detail(existing.range.clone(), "the module's default export is first defined here"));
            clause.change_kind(p, JsSyntaxKind::JS_BOGUS);
        }
    }
    // TypeScript merges multiple `export default interface`; never stored:
    else if !default_item_kind.is_interface() {
        p.state_mut().default_item = Some(ExportDefaultItem { range: clause.range(p).into(), kind: default_item_kind });
    }
    clause
})
```

**Flow:** dispatch on the token after `export default` (@-decorated classes re-enter a dedicated ladder; functions inspect the parsed declaration kind to distinguish overload from implementation) → map to an item kind → single mergeability check against the stored item.
**Invariant:** The check is gated on `p.is_module()` — scripts never enforce it, so `export` in a script errors elsewhere without poisoning this state. The *first* interface isn't stored, so N interfaces all pass while `interface` then `function` still collides via the function being stored. Duplicate-default demotion changes only the clause kind to `JS_BOGUS`, keeping tokens losslessly attached for later tooling.
**Probe:** `crates/biome_js_parser/tests/js_test_suite/error/multiple_default_exports_err.js` (`export default (class {})` twice, expression + function mixes).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "biome", query: "ExportDefaultItemKind is_mergeable default_item", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the typed item-kind + mergeability-pair model for any per-module uniqueness rule; adapt kinds; omit the script/module gate if the host has no dual goal. Coverage caveat: full-mode index, metadata_match.
