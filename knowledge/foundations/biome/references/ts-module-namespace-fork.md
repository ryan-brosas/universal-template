<!-- capsule-v2 -->
# Namespace/module/global fork — how does one entry point split ambient namespaces, external module declarations, global augmentation, and `import x = require(...)`?

**Source:** Biome MIT `main@6cd32636f463551b8dfe46aeefb1191d437b4694`; Codebase Memory `biome`. **Question:** How do I port TS namespace-form parsing with correct body-vs-semi handling for string-module names?

## parse_any_ts_namespace_declaration_statement family
**Path/Symbol:** `crates/biome_js_parser/src/syntax/typescript/statement.rs:is_nth_at_any_ts_namespace_declaration` (:398-412), `parse_any_ts_namespace_declaration_clause` (:414-425), `parse_ts_namespace_or_module_declaration_clause` (:451-487), `parse_ts_module_name` (:494-505), `parse_ts_global_declaration` (:539-548), `parse_ts_import_equals_declaration_rest` (:559-581), `parse_ts_external_module_reference` (:583-595).
**Signature:** probe `fn is_nth_at_any_ts_namespace_declaration(p, n) -> bool`; main fork returns `TS_MODULE_DECLARATION | TS_EXTERNAL_MODULE_DECLARATION | TS_GLOBAL_DECLARATION`.
**Data Shape:** Probe: `global` valid ONLY if followed by `{`; `namespace|module` need same-line + identifier or STRING literal at n+1. String source forks the whole shape: `module "a";` / `module "a" {}` → TS_EXTERNAL_MODULE_DECLARATION.

### Decisive source
```rust
if !p.eat(T![namespace]) {
    p.expect(T![module]);
    if p.at(JS_STRING_LITERAL) {
        parse_module_source(p).expect(…);
        let body = parse_ts_module_block(p);
        if body.is_absent() {                       // `declare module "a";`
            if p.at(T![;]) {
                let body = p.start(); p.bump(T![;]);
                body.complete(p, TS_EMPTY_EXTERNAL_MODULE_DECLARATION_BODY);
            } else {
                semi(p, TextRange::new(stmt_start_pos, p.cur_range().end()));
            }
        }
        return Present(m.complete(p, TS_EXTERNAL_MODULE_DECLARATION));
    }
}
parse_ts_module_name(p).or_add_diagnostic(p, expected_identifier);   // dotted a.b.c
parse_ts_module_block(p).or_add_diagnostic(p, |_, _| expected_token(T!['{']));
Present(m.complete(p, TS_MODULE_DECLARATION))
```
Import-equals tail (entered from module.rs after `import`):
```rust
if is_nth_at_identifier_binding(p, 1) { p.eat(T![type]); }  // import type A = …
parse_identifier_binding(p).or_add_diagnostic(p, expected_identifier);
p.expect(T![=]);
if p.at(T![require]) { parse_ts_external_module_reference(p).expect(…) }
else                 { parse_ts_name(p).or_add_diagnostic(p, expected_identifier); }
semi(p, TextRange::new(stmt_start_pos, p.cur_range().end()));
m.complete(p, TS_IMPORT_EQUALS_DECLARATION)
```

**Flow:** stmt dispatch on `module|namespace|global` (gated by probe, exclusive-syntax wrapped) → string-literal source takes the EXTERNAL branch (module-source parse reuses the module grammar's string validation) → otherwise qualified-name chain (`TS_QUALIFIED_MODULE_NAME` built by precede-loop over `.`) → block body of full module items via `parse_module_item_list(ModuleItemListParent::Block)`. `global` alone → TS_GLOBAL_DECLARATION wrapping only a block.
**Invariant:** The missing-body recovery has THREE shapes that must not be merged: absent block after string source + `;` → dedicated TS_EMPTY_EXTERNAL_MODULE_DECLARATION_BODY node (bumps the semicolon INTO the body); absent block without `;` → plain `semi()` spanning statement start; non-string module/namespace missing `{` → expected-token diagnostic. `global` must NOT accept identifiers (it's only an augmentation head) — the probe encodes this before dispatch. The `type` modifier in import-equals is eaten only when nth(1) is an identifier BINDING, so `import type from "x"` never reaches this path.
**Probe:** `crates/biome_js_parser/tests/js_test_suite/error/ts_module_err.ts` (`declare module a;`, `declare module "a" declare module "b";`) vs `…/ok/ts_global_declaration.ts` (incl. `declare global\n{ }` across a line break) and `…/ok/ts_import_equals_declaration.ts` (require/name/type-modifier/export-import forms).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "biome", query: "parse_ts_namespace_or_module_declaration_clause parse_ts_import_equals_declaration_rest", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the three-way body-recovery split and the global-needs-block probe; adapt qualified-name construction to your AST's qualified-name node; omit the require() arm in ESM-only hosts.
