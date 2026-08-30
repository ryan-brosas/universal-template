<!-- capsule-v2 -->
# Directive prologue with marker surgery — how do you retroactively reclassify already-parsed nodes ("use strict")?

**Source:** Biome MIT `main@6cd32636f463551b8dfe46aeefb1191d437b4694`; Codebase Memory `biome`. **Question:** How do you parse string-literal statements, then turn them into directives and flip parser state — including the case where a "directive" turns out to be `"use strict".length`?

## parse_directives
**Path/Symbol:** `crates/biome_js_parser/src/syntax/stmt.rs:parse_directives` (:839-887), consumer `parse_block_impl` (:771-794).
**Signature:** `pub(crate) fn parse_directives(p: &mut JsParser) -> (Marker, Option<EnableStrictModeSnapshot>)`
**Data Shape:** Returns the statement-list marker (possibly *already containing* one parsed expression statement) plus an optional strict-mode snapshot to restore at block end.

### Decisive source
```rust
// Something like "use strict".length isn't a valid directive
if expression.kind(p) != JS_STRING_LITERAL_EXPRESSION {
    // Turned out not to be a directive.
    // Start statement list before the just parsed expression statement
    let statement = expression.precede(p).complete(p, JS_EXPRESSION_STATEMENT);
    break statement.precede(p);
}
// ...
let directive = expression.undo_completion(p);   // expression -> bare literal again
semi(p, directive_range);
// ...
directive.complete(p, JS_DIRECTIVE);
// Extend the directive list to include the just parsed directive
directives_list = directives_list.undo_completion(p).complete(p, JS_DIRECTIVE_LIST);
```

**Flow:** while `cur` is a string literal: parse it as an expression → if it's a plain string-literal expression, `undo_completion` (expression → its inner literal), attach as `JS_DIRECTIVE`, then `undo_completion`+re-`complete` the directive list to grow it → else complete the expression as an ordinary `JS_EXPRESSION_STATEMENT` and start the statement list from it. First `"use strict"`/`'use strict'` applies `EnableStrictMode(StrictMode::Explicit(range))`; the snapshot is restored by the caller after the closing `}`.
**Invariant:** Only the FIRST directive can enable strict mode (`strict_mode_snapshot.is_none()` gate) but later directives still become `JS_DIRECTIVE` nodes. The list-extension dance works because markers are stack indices: undo/complete is cheap and doesn't move events. Directives are only recognized in function bodies (`parse_block_impl(JS_FUNCTION_BODY)`); plain blocks enter with a bare `p.start()` marker and no strict handling. The caller restores state after the closing brace via `EnableStrictMode::restore(p.state_mut(), strict_snapshot)` (:789-791) — dropping that call leaks strict mode past the function body.
**Probe:** `crates/biome_js_parser/tests/js_test_suite/ok/directives.cjs` + `directives_redundant.cjs` (covers `"use new"`, nested functions, `"use strict".length` non-directive).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "biome", query: "parse_directives undo_completion directive strict", limit: 10, fields: ["signature", "name", "file"] });
```
Resolves `marker.CompletedMarker.undo_completion` (:217-238).

## Verdict
Adopt marker undo/re-complete surgery for any production whose classification of leading tokens changes after more input; adapt the specific directive semantics; omit strict-mode plumbing in languages without it.
