<!-- capsule-v2 -->
# Parameter-list driver loop — how does a generic list parser handle separators, missing items, metavariables, and bogus recovery without infinite loops?

**Source:** Biome MIT `main@6cd32636f463551b8dfe46aeefb1191d437b4694`; Codebase Memory `biome`. **Question:** What is the reusable driver for comma-separated parameter lists (and how do state flags, object-expression gating, and recovery-on-line-break compose inside it)?

## parse_parameters_list closure-driven loop
**Path/Symbol:** `crates/biome_js_parser/src/syntax/function.rs:parse_parameter_list` (:1320-1416) and `parse_parameters_list` (:1419-1495).
**Signature:** `fn parse_parameters_list(p: &mut JsParser, flags: SignatureFlags, parse_parameter: impl Fn(&mut JsParser, ExpressionContext) -> ParsedSyntax, list_kind: JsSyntaxKind)` — the per-item grammar is injected as a closure; `parse_parameter_list` wraps it into `JS_PARAMETERS` with decorator context selection.
**Data Shape:** Structure `JS_PARAMETERS` ⊃ `JS_PARAMETER_LIST` (inner started inside `EnterParameters(flags)`) ⊃ items. Decorators: allowed only when `parameter_context.is_any_class_method()`; otherwise diagnostic + `change_to_bogus`.

### Decisive source
```rust
let mut first = true;
let has_l_paren = p.expect(T!['(']);
p.with_state(EnterParameters(flags), |p| {
    let parameters_list = p.start();
    let mut progress = ParserProgress::default();
    while !p.at(EOF) && !p.at(T![')']) {
        if first { first = false; } else { p.expect(T![,]); }
        if p.at(T![')']) { break; }          // trailing comma: exit cleanly
        progress.assert_progressing(p);      // hard guarantee against no-progress loops
        if parse_metavariable(p).is_present() { continue; }
        let parameter = parse_parameter(
            p,
            ExpressionContext::default().and_object_expression_allowed(!first || has_l_paren),
        );
        if parameter.is_absent() && p.at(T![,]) {
            // a missing parameter,
            parameter.or_add_diagnostic(p, expected_parameter);
            continue;                        // `(a,,b)` = hole, not failure
        }
        let recovered_result = parameter.or_recover_with_token_set(
            p,
            &ParseRecoveryTokenSet::new(JS_BOGUS_PARAMETER,
                token_set![T![ident], T![await], T![yield], T![this], T![,],
                           T!['['], T![...], T!['{'], T![')'], T![;]])
                .enable_recovery_on_line_break(),
            js_parse_error::expected_parameter,
        );
        if recovered_result.is_err() { break; }
    }
    parameters_list.complete(p, list_kind);
});
p.expect(T![')']);
```

**Flow:** expect `(` → enter parameter state (flags make `await`/`yield` binding-legal per signature) → loop { separator (skip on first), early-exit on `)` after separator (trailing comma), progress assertion, metavariable short-circuit (`%name%` macro slots — see slot-factory capsule's sibling), injected item parse → absent+`,` ⇒ named hole; absent otherwise ⇒ recover into `JS_BOGUS_PARAMETER`, stopping at restart tokens or line breaks; unrecoverable ⇒ break and let the outer `expect(')')` report } → complete inner list, expect `)`.
**Invariant:** The object-expression gate is positional: `{` starts an object *binding pattern* for the first parameter but an object expression is only allowed from the second parameter onward (`!first || has_l_paren`) — flipping this misparses `function f({a}, {b})`. `ParserProgress::assert_progressing` must wrap every iteration that can consume nothing (holes/metavariables). Recovery token set includes `,`/`)`/`;` so one bad parameter never swallows the list.
**Probe:** `crates/biome_js_parser/tests/js_test_suite/error/formal_params_invalid.js` (`function (a++, c)`) and `error/formal_params_no_binding_element.js` (`function foo(true)`); hole syntax pinned by `ok/parameter_list.js` (`function evalInComputedPropertyKey({ [computed]: ignored }) {}`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "biome", query: "parse_parameters_list ParserProgress or_recover_with_token_set bogus parameter", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the driver shape (injected item closure + first-flag separator + hole handling + bounded recovery set + progress assertion) for any comma-separated list; adapt node kinds; omit Biome token spellings. This is the repo's most-reused list-parsing skeleton beyond `list-parsing.md`.
