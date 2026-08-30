<!-- capsule-v2 -->
# Non-top-level import/export demotion — parse the full declaration, then bogus it with a module-kind-aware message

**Source:** Biome MIT `main@6cd32636f463551b8dfe46aeefb1191d437b4694`; Codebase Memory `biome`. **Question:** How does a statement-level parser handle `import`/`export` appearing inside blocks or scripts without losing the CST or mis-detecting `import.meta`/`import()`?

## parse_statement import arm + parse_non_top_level_export
**Path/Symbol:** `crates/biome_js_parser/src/syntax/stmt.rs:parse_statement` (:158-192), `parse_non_top_level_export` (:382-406).
**Signature:** `T![import] if !token_set![T![.], T!['(']].contains(p.nth(1)) => ...`; `pub(crate) fn parse_non_top_level_export(p: &mut JsParser, decorator_list: ParsedSyntax) -> ParsedSyntax`.
**Data Shape:** The complete declaration is parsed first (via `parse_import_or_import_equals_declaration` / `parse_export`), then: `TS_IMPORT_EQUALS_DECLARATION` is returned as-is (it is legal in nested TS scopes); anything else gets `import.change_kind(p, JS_BOGUS_STATEMENT)` + one diagnostic whose text branches on `p.source_type().module_kind()`.

### Decisive source
```rust
// make sure we dont try parsing import.meta or import() as declarations
T![import] if !token_set![T![.], T!['(']].contains(p.nth(1)) => {
    let mut import = parse_import_or_import_equals_declaration(p).unwrap();
    if import.kind(p) == TS_IMPORT_EQUALS_DECLARATION { return Present(import); }
    import.change_kind(p, JS_BOGUS_STATEMENT);
    let error = match p.source_type().module_kind() {
        ModuleKind::Script => p.err_builder("Illegal use of an import declaration outside of a module", ...)
            .with_hint("not allowed inside scripts"),
        ModuleKind::Module => p.err_builder("Illegal use of an import declaration not at the top level", ...)
            .with_hint("move this declaration to the top level"),
    };
    p.error(error); Present(import)
}
```

**Flow:** dispatch guard excludes `.` and `(` so dynamic `import()` / `import.meta` fall through to expression parsing; the declaration parser runs UNCONDITIONALLY (even in guaranteed-illegal positions) because it must consume a deterministic token span for recovery; only afterwards is the completed node demoted and the message chosen by module kind vs position.
**Invariant:** Never bail before consuming — an early `Absent` would leave the block-statement loop to recover over the whole import as one bogus blob, degrading every subsequent diagnostic. The `TS_IMPORT_EQUALS` early-return means legality is kind-dependent, not keyword-dependent. Export mirrors this exactly (`parse_non_top_level_export` wraps any decorator list too).
**Probe:** `crates/biome_js_parser/tests/js_test_suite/error/import_decl_not_top_level.js(.snap)` and `error/export_decl_not_top_level.js` (nested module items recovered per-item, not swallowed).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "biome", query: "parse_non_top_level_export change_kind JS_BOGUS_STATEMENT ModuleKind", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt "parse-then-demotion" for positionally illegal but grammatically known constructs; adapt the module-kind discriminator to host file-source model; omit wording.
