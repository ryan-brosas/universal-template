<!-- capsule-v2 -->
# Switch-case recovery synthesis — how do you recover garbage between `case` labels into a well-shaped node?

**Source:** Biome MIT `main@6cd32636f463551b8dfe46aeefb1191d437b4694`; Codebase Memory `biome`. **Question:** How does a list's `recover` hook fabricate missing intermediate nodes so the tree still matches the grammar?

## SwitchCasesList::recover
**Path/Symbol:** `crates/biome_js_parser/src/syntax/stmt.rs:SwitchCasesList` (:1873-1932), clause parser `parse_switch_clause` (:1822-1872), statement list `SwitchCaseStatementList` (:1794-1819).
**Signature:** `fn recover(&mut self, p: &mut JsParser, parsed_element: ParsedSyntax) -> RecoveryResult` (from the `ParseNodeList` trait).
**Data Shape:** On success path builds `JS_CASE_CLAUSE { JS_STATEMENT_LIST { JS_BOGUS_STATEMENT } }`; tracks `first_default: Option<TextRange>` for duplicate-default reporting.

### Decisive source
```rust
fn recover(&mut self, p: &mut JsParser, parsed_element: ParsedSyntax) -> RecoveryResult {
    if let Present(marker) = parsed_element { return Ok(marker); }
    let m = p.start();
    let statements = p.start();
    let recovered_element = parsed_element.or_recover_with_token_set(
        p,
        &ParseRecoveryTokenSet::new(JS_BOGUS_STATEMENT, token_set![T![default], T![case], T!['}']])
            .enable_recovery_on_line_break(),
        js_parse_error::expected_case_or_default,
    );
    match recovered_element {
        Ok(marker) => {
            statements.complete(p, JS_STATEMENT_LIST);
            m.complete(p, JS_CASE_CLAUSE);   // synthesize the missing clause wrapper
            Ok(marker)
        }
        Err(err) => { statements.abandon(p); m.abandon(p); Err(err) }
    }
}
```

**Flow:** element parse returns Absent (junk where a case should be) → open markers for a clause + its statement list → recovery consumes tokens until `case`/`default`/`}`/line-break as one bogus statement → if recovery succeeded, complete BOTH synthetic nodes so the switch's `JS_SWITCH_CASE_LIST` slot shape holds; if even recovery failed (e.g. EOF), abandon both and propagate.
**Invariant:** The bogus statement is wrapped so downstream AST consumers can assume every child of a case list is a `JS_CASE_CLAUSE`. Duplicate defaults take a different trick: the second `default` keyword is parsed as a *bogus test expression* of a normal `JS_CASE_CLAUSE` (:1828-1836) — keeping exactly one real `JS_DEFAULT_CLAUSE`.
**Probe:** `crates/biome_js_parser/tests/js_test_suite/error/switch_stmt_err.js` (includes `switch (foo) { default: default: }`) vs `ok/switch_stmt.js`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "biome", query: "SwitchCasesList recover case clause", limit: 10, fields: ["signature", "name", "file"] });
```
Resolves `syntax.stmt.SwitchCasesList.recover` (:1901-1931).

## Verdict
Adopt recover-hook node synthesis to preserve grammar shape under errors; adapt recovery token sets; omit the duplicate-default reclassification if your AST allows multiple defaults. Pairs with the existing `list-parsing.md` capsule (loop mechanics) — this one is the per-list recovery *policy*.
