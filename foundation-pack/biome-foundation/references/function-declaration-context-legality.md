<!-- capsule-v2 -->
# Function declaration context legality — why is the same `function f(){}` sometimes parsed fine, sometimes an error-with-bogus, and how do single-statement and ambient contexts change its kind?

**Source:** Biome MIT `main@6cd32636f463551b8dfe46aeefb1191d437b4694`; Codebase Memory `biome`. **Question:** How does a function declaration encode statement-position legality (strict mode, if/label exemption) and ambient-context rules into node kinds without a second pass?

## parse_function_declaration + parse_ambient_function
**Path/Symbol:** `crates/biome_js_parser/src/syntax/function.rs:parse_function_declaration` (:69-111), `FunctionKind` helpers (:146-199), `parse_ambient_function` (:388-472).
**Signature:** `fn parse_function_declaration(p: &mut JsParser, context: StatementContext) -> ParsedSyntax`; `AmbientFunctionKind::{Declaration, ExportDefault}`.
**Data Shape:** Legal-in-context ⇒ `JS_FUNCTION_DECLARATION`; violation ⇒ *parsed anyway* then `change_to_bogus` + error. Ambient: async ⇒ `JS_BOGUS_STATEMENT`; generator ⇒ error but continues; body present ⇒ "declare function cannot have a body" error; completes `TS_DECLARE_FUNCTION_DECLARATION(_EXPORT_DEFAULT)`.

### Decisive source
```rust
if context != StatementContext::StatementList && !function.kind(p).is_bogus() {
    if JsSyntaxFeature::StrictMode.is_supported(p) {
        p.error(p.err_builder("In strict mode code, functions can only be declared at top level or inside a block", function.range(p)).with_hint("wrap the function in a block statement"));
        function.change_to_bogus(p);
    } else if !matches!(context, StatementContext::If | StatementContext::Label) {
        // loose mode annex-B: allowed ONLY as the direct body of if / labelled statement
        p.error(...);
        function.change_to_bogus(p);
    }
}
```
And the id rule split in `parse_function_id`: Expression kind re-enters with its own flags (`p.with_state(EnterFunction(flags), parse_binding)`) so `(function await(){})` is legal while nested `function yield(){}` inside a generator errors — declarations inherit parent restrictions instead.
**Flow:** dispatch on ambient context first (`in_ambient_context()` ⇒ ambient variant) → parse full function → post-hoc context check demotes to bogus. Ambient variant: report-and-continue for async/generator (flags NOT set), require no body, `semi()` before completing declare-kind.
**Invariant:** Legality is checked **after** parsing completes, on the completed marker's range — never by pre-scanning. The if/label exemption exists only in loose mode and only for those exact two contexts. Ambient functions still run the full parameter/return-type grammar (Declaration parameter context), so downstream tooling sees one uniform signature shape.
**Probe:** `crates/biome_js_parser/tests/js_test_suite/error/function_in_single_statement_context_strict.js` (`if (true) function a(){}`, label case) and `ok/function_in_if_or_labelled_stmt_loose_mode.js` (script-mode exemption); ambient pins in `ok/ts_declare_function.ts`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "biome", query: "parse_function_declaration single_statement_context change_to_bogus ambient", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt parse-then-classify (post-hoc demotion over speculative rejection) and the strict/loose + if/label matrix; adapt StatementContext variants; omit message text. The ambient path's report-and-continue style pairs with the overload-deferral capsule.
