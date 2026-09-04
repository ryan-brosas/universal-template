<!-- capsule-v2 -->
# TS-exclusive dialect gate — how does a shared parser accept TypeScript syntax in .ts and demote it to bogus (not skip) in .js?

**Source:** Biome MIT `main@6cd32636f463551b8dfe46aeefb1191d437b4694`; Codebase Memory `biome`. **Question:** When porting a multi-dialect parser, how should TS-only constructs be handled in a JS file so error recovery still produces a tree instead of abandoning the statement?

## SyntaxFeature::parse_exclusive_syntax
**Path/Symbol:** `crates/biome_parser/src/lib.rs:parse_exclusive_syntax` (:660-687), trait impl `SyntaxFeature` on `TypeScript` / `EcmaScript`; paired emitter `crates/biome_js_parser/src/syntax/typescript/ts_parse_error.rs:ts_only_syntax_error`.
**Signature:** `fn parse_exclusive_syntax<P, E>(&self, p, parse: P, error_builder: E) -> ParsedSyntax where P: FnOnce(&mut Parser) -> ParsedSyntax, E: FnOnce(&Parser, &CompletedMarker) -> ParseDiagnostic`.
**Data Shape:** `self` is the dialect feature (`TypeScript.is_supported(p)` consults file-source language); `parse` is the TS-only sub-parser; `error_builder` turns the *successfully parsed* node into the "TS-only" diagnostic. Output: `Present(bogus-demoted node)` or `Absent`.

### Decisive source
```rust
if self.is_supported(p) {
    parse(p)
} else {
    let diagnostics_checkpoint = p.context().diagnostics().len();
    let syntax = parse(p);
    p.context_mut().truncate_diagnostics(diagnostics_checkpoint); // swallow inner diags
    match syntax {
        Present(mut syntax) => {
            let diagnostic = error_builder(p, &syntax);
            p.error(diagnostic);
            syntax.change_to_bogus(p);          // keep shape, mark bogus
            Present(syntax)
        }
        _ => Absent,
    }
}
```
Call-site pattern (stmt.rs dispatch):
```rust
T![const] | T![enum] if is_at_ts_enum_declaration(p) => {
    // test_err js enum_in_js
    TypeScript.parse_exclusive_syntax(p, parse_ts_enum_declaration, |p, declaration| {
        ts_only_syntax_error(p, "'enum's", declaration.range(p))
    })
}
```

**Flow:** dialect gate checks file source FIRST → supported: parse normally → unsupported: checkpoint diagnostics, run the TS parser SPECULATIVELY, truncate whatever inner diagnostics it emitted, emit exactly one outer "TS-only" diagnostic at the completed node's range, then `change_to_bogus`. Callers gate with precise predicates (`is_at_ts_enum_declaration`, `is_at_ts_interface_declaration`, `is_at_ts_declare_statement`, `is_nth_at_any_ts_namespace_declaration`) so plain-JS parses of the same keyword never enter this path.
**Invariant:** The speculative parse must leave the token cursor where the TS grammar would have left it — the bogus node spans what the construct consumed. Diagnostics from inside are suppressed so the user gets ONE clear message, not a cascade of confusing inner errors; truncating BEFORE building the outer diagnostic is order-sensitive. A porter who skips the checkpoint/truncate pair emits double diagnostics; one who skips `change_to_bogus` emits a valid-looking TS node inside a .js file.
**Probe:** `crates/biome_js_parser/tests/js_test_suite/error/enum_in_js.js` (JS file: `enum A {}` → single ts_only error + bogus node) vs `crates/biome_js_parser/tests/js_test_suite/ok/typescript_enum.ts` (same text in .ts parses clean).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "biome", query: "parse_exclusive_syntax SyntaxFeature is_supported", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the checkpoint→speculative-parse→truncate→single-diagnostic→bogus pipeline for any cross-dialect parser; adapt `is_supported` to your own file-source enum; omit the EcmaScript-side no-op variant when your host has a single dialect.
