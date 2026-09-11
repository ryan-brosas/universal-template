<!-- capsule-v2 -->
# Cover-grammar assignment repattern — how do you parse `[a, b] = c` when your expression parser already consumed it as an array literal?

**Source:** Biome MIT `main@6cd32636f463551b8dfe46aeefb1191d437b4694`; Codebase Memory `biome`. **Question:** How does a recursive-descent parser accept destructuring targets on the left of `=` without duplicating the grammar, given that `{a: 1} = x` is only distinguishable from an object literal *after* the whole expression has been parsed?

## expression_to_assignment_pattern + parse_assignment_pattern
**Path/Symbol:** `crates/biome_js_parser/src/syntax/assignment.rs:expression_to_assignment_pattern` (:82-98), `parse_assignment_pattern` (:117-123), `AssignmentExprPrecedence` (:148-160).
**Signature:** `fn expression_to_assignment_pattern(p: &mut JsParser, target: CompletedMarker, checkpoint: JsParserCheckpoint) -> ParsedSyntax`.
**Data Shape:** Input is the `CompletedMarker` produced by `parse_conditional_expr` plus the checkpoint taken *before* that call. Output is either a re-parsed pattern (object/array case) or an in-place rewritten assignment (`expression_to_assignment`). Failure shape: `Err(CompletedMarker)` from the rewrite visitor becomes `JS_BOGUS_ASSIGNMENT` + one error.

### Decisive source
```rust
pub(crate) fn parse_assignment_pattern(p: &mut JsParser) -> ParsedSyntax {
    let checkpoint = p.checkpoint();
    let assignment_expression = parse_conditional_expr(p, ExpressionContext::default());
    assignment_expression
        .and_then(|expression| expression_to_assignment_pattern(p, expression, checkpoint))
}

match target.kind(p) {
    JS_OBJECT_EXPRESSION => { p.rewind(checkpoint); ObjectAssignmentPattern.parse_object_pattern(p) }
    JS_ARRAY_EXPRESSION => { p.rewind(checkpoint); ArrayAssignmentPattern.parse_array_pattern(p) }
    _ => ParsedSyntax::Present(expression_to_assignment(p, target, checkpoint)),
}
```

**Flow:** take checkpoint → parse a conditional expression unconditionally → inspect its completed kind → if it was an object/array *literal*, rewind to the checkpoint and re-parse as pattern grammar; otherwise keep the tree and let `ReparseAssignment` relabel kinds in place.
**Invariant:** The checkpoint must be captured before the speculative expression parse — rewinding after the fact is what makes the "parse as the more general grammar, fall back" strategy lossless. The precedence split (`Conditional` vs `Unary`) exists because `for (x = 1;;)` and `for (x in y)` need different LHS ceilings; a porter who hardcodes one ceiling breaks `for ((a = b) in c)` style cases.
**Probe:** `crates/biome_js_parser/tests/js_test_suite/ok/array_assignment_target.js` (pins `[a = "test", a.b, call().b] = baz`, `((a)) = baz`) alongside `error/invalid_assignment_target.js`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "biome", query: "expression_to_assignment_pattern parse_assignment_pattern", limit: 10, fields: ["signature", "name", "file"] });
```
Resolves `syntax.assignment.expression_to_assignment_pattern` (:82-98).

## Verdict
Adopt cover-grammar parsing via checkpoint + kind-dispatch + rewind-reparse for any grammar with genuinely ambiguous constructs (JS destructuring, TS arrow-vs-type-cast); adapt the kind set to the host language's node vocabulary; omit Biome's metavariable escape hatch unless porting into Grit-style templating. Coverage caveat: full-mode index, metadata_match at generation 2026-08-16T00:20:04Z.
