<!-- capsule-v2 -->
# Kind-parameterized pattern traits — how do you parse array/object binding patterns AND assignment targets from one grammar with different node kinds?

**Source:** Biome MIT `main@6cd32636f463551b8dfe46aeefb1191d437b4694`; Codebase Memory `biome`. **Question:** How does one list-parsing implementation produce `JS_ARRAY_BINDING_PATTERN` for `let [a] = b` and `JS_ARRAY_ASSIGNMENT_PATTERN` for `[a] = b` without copy-pasting the loops?

## ParseWithDefaultPattern / ParseArrayPattern<P> / ParseObjectPattern
**Path/Symbol:** `crates/biome_js_parser/src/syntax/pattern.rs:ParseWithDefaultPattern` (:13-37), `ParseArrayPattern<P>` (:40-133), `ParseObjectPattern` (:136-216), free fn `validate_rest_pattern` (:225-281).
**Signature:** `fn parse_pattern_with_optional_default(&self, p: &mut JsParser) -> ParsedSyntax` (provided method); implementors supply only kinds + error builders + an element parser.
**Data Shape:** Each impl is a zero-sized struct (`ArrayBindingPattern`, `ObjectAssignmentPattern`, …) whose trait methods return `JsSyntaxKind`s: bogus kind, pattern kind, rest kind, list kind. The generic loop carries a `ParseRecoveryTokenSet` built from `token_set!(EOF, , ], = ; ... )`) with line-break recovery.

### Decisive source
```rust
// provided method wraps ANY inner pattern in a default clause
self.parse_pattern(p).and_then(|pattern| {
    let m = pattern.precede(p);
    parse_initializer_clause(p, ExpressionContext::default()).ok();
    Present(m.complete(p, Self::pattern_with_default_kind()))
})

// holes are explicit nodes, not skipped commas:
match p.cur() {
    T![,] => Present(p.start().complete(p, JS_ARRAY_HOLE)),
    T![...] => self.parse_rest_pattern(p).map(|r| validate_rest_pattern(p, r, T![']'], recovery)),
    _ => self.pattern_with_default().parse_pattern_with_optional_default(p),
}
```

**Flow:** guard on opening token → start marker → bump → inner list marker + `ParserProgress` → per element: hole / rest / pattern-with-optional-default, each wrapped in recovery; recovery failure breaks the loop → complete list kind → expect closer → complete pattern kind.
**Invariant:** Rest validation is centralized: a rest must be last, have no default, and no trailing comma — violations *undo* or demote the completed marker (`rest.change_to_bogus`, and for a stray default the completion is literally undone via `undo_completion` so the default tokens attach to the bogus node). Array holes exist as real `JS_ARRAY_HOLE` nodes because slot positions carry meaning — a porter who collapses `[a,,b]` to two elements breaks positional destructuring.
**Probe:** `crates/biome_js_parser/tests/js_test_suite/ok/array_assignment_target.js` + `error/array_assignment_target_rest_err.js` (`[...c = "default"]`, `[...rest, other]`, trailing-comma rest all pinned).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "biome", query: "validate_rest_pattern ParseArrayPattern parse_array_pattern", limit: 10, fields: ["signature", "name", "file"] });
```
Resolves `syntax.pattern.validate_rest_pattern` (:225-281).

## Verdict
Adopt the kind-parameterized trait family as the template for any dual-life grammar (pattern vs expression, statement vs declaration); adapt kinds/diagnostics per host; omit the metavariable hooks if not building a templating layer. Coverage caveat: full-mode index, metadata_match.
