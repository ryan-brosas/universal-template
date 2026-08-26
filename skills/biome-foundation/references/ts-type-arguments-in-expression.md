<!-- capsule-v2 -->
# Type-arguments-in-expression speculation — when does `f<T>(…)` keep its type arguments and `a < b > c` stay comparisons?

**Source:** Biome MIT `main@6cd32636f463551b8dfe46aeefb1191d437b4694`; Codebase Memory `biome`. **Question:** What is the full accept/reject contract (re-lexing + follower heuristic) for speculative type arguments in expression position, and how does recovery toggling differ between speculative and committed parses?

## parse_ts_type_arguments_in_expression
**Path/Symbol:** `crates/biome_js_parser/src/syntax/typescript/types.rs:parse_ts_type_arguments_in_expression` (:2128-2164), `can_follow_type_arguments_in_expr` (:2166-2183), recovery toggle in `TypeArgumentsList::recover` (:2243-2269).
**Signature:** `fn parse_ts_type_arguments_in_expression(p: &mut JsParser, context: ExpressionContext) -> ParsedSyntax` — TS-only (`TypeScript.is_unsupported(p)` ⇒ Absent), at `<` or `<<`.
**Data Shape:** `TypeArgumentsList { context, recover_on_errors }` — the SAME list type serves both modes; trailing separators disallowed here (`allow_trailing_separating_element() == false`, unlike type *parameters*).

### Decisive source
```rust
try_parse(p, |p| {
    p.re_lex(JsReLexContext::TypeArgumentLessThan);  // '<<' → '<'
    let m = p.start();
    p.bump(T![<]);
    if p.at(T![>]) { p.error(expected_ts_type_parameter(p, p.cur_range())); }
    TypeArgumentsList::new(TypeContext::default(), false).parse_list(p);
    p.re_lex(JsReLexContext::BinaryOperator);        // '>>' back to real operators
    p.expect(T![>]);
    let arguments = m.complete(p, TS_TYPE_ARGUMENTS);
    if p.last() == Some(T![>]) && can_follow_type_arguments_in_expr(p, context) {
        Ok(Present(arguments))
    } else {
        Err(())   // rewind whole attempt → plain comparison expression
    }
}).unwrap_or(Absent)
```
Follower heuristic:
```rust
T!['('] | BACKTICK | EOF => true,
T![<] | T![>] | T![+] | T![-] => false,   // ambiguous with shifts/unary — reject
_ => p.has_preceding_line_break() || is_at_binary_operator(p, context) || !is_at_expression(p),
```
Recovery toggle:
```rust
if parsed_element.is_absent() && !self.recover_on_errors {
    // Parse conditional expression speculatively tries to parse a list of type arguments
    // The parser shouldn't perform error recovery in that case and simply bail out of parsing
    RecoveryResult::Err(RecoveryError::AlreadyRecovered)
} else { /* normal bogus-type recovery */ }
```

**Flow:** re-lex `<` out of `<<` → parse list with recovery OFF → re-lex closing `>` back into binary operators (`a<b>>c`) → accept only if last token was exactly `>` AND the follower heuristic passes → else Err ⇒ full rewind. Committed contexts (`parse_ts_type_arguments`) use the same list with `recover_on_errors = true`.
**Invariant:** Two coupled contracts: (1) inside speculation, list errors must NOT be recovered into bogus nodes — they'd leak past the rewind as diagnostics; (2) the accept check happens on the *post-relex* token stream, so `f<T> >> f<T>` correctly fails while `f<x> ? g<y> : h<z>` passes. The `< > + -` rejection exists because those followers are ambiguous even after relex.
**Probe:** `crates/biome_js_parser/tests/js_test_suite/ok/ts_type_arguments_like_expression.ts` (`0 < (0 >= 1)` stays comparison) plus the instantiation-expression matrix in types.rs comments (:1881-2126, incl. `f<T>\n?? 1` ASI cases).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "biome", query: "can_follow_type_arguments_in_expr re_lex TypeArgumentLessThan", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt speculate-with-recovery-off + post-relex follower test for any `<`/`>` ambiguity; adapt relex contexts to host lexer (see lexer-buffered.md); omit Biome's exact follower set where host grammar differs. Distinct from arrow-speculation-memo.md (that memoizes failure by position; this one re-decides via relex each time).
