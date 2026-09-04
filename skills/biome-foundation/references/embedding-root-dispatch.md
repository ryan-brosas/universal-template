<!-- capsule-v2 -->
# Embedding-aware root dispatch — how does one JS parser entry point serve scripts, modules, `.d.ts`, Vue handlers, Svelte snippets, and template expressions without duplicating the grammar?

**Source:** Biome MIT `main@6cd32636f463551b8dfe46aeefb1191d437b4694`; Codebase Memory `biome`. **Question:** How should a parser root branch on source *embedding kind* (not file extension) so `{ duration }` parses as an object literal, never a block?

## program::parse root dispatch
**Path/Symbol:** `crates/biome_js_parser/src/syntax/program.rs:parse` (:31-77), `parse_vue_event_handler` (:156-203), `parse_template_expression` (:106-154), `parse_snippet_signature` (:208-231).
**Signature:** `fn parse(p: &mut JsParser) -> CompletedMarker` — BOM + shebang eaten first, then `p.source_type()` predicates choose the root grammar.
**Data Shape:** Roots: `JS_SCRIPT` / `JS_MODULE` / `TS_DECLARATION_MODULE` / `JS_EXPRESSION_TEMPLATE_ROOT` / `JS_SVELTE_DECLARATION_ROOT` / `JS_SVELTE_SNIPPET_ROOT`. Vue handler sets: member/identifier/arrow/function expressions = handlers; everything else = inline statement.

### Decisive source
```rust
// Vue event handlers use Vue's own heuristic: member/function expressions
// are handlers, and all other expressions are inline statements.
if p.at(EOF) && VUE_EXPRESSION_HANDLER_SET.contains(expression_kind) {
    expr_marker.abandon(p);
    return m.complete(p, JS_EXPRESSION_TEMPLATE_ROOT);
}
// …but a function-expression "handler" with trailing code rewinds to statement parsing:
expr_marker.abandon(p);
p.rewind(checkpoint);
let (statement_list, strict_snapshot) = parse_directives(p);
parse_statements(p, false, statement_list);   // → JS_SCRIPT
```
Template-expression trailing guard:
```rust
if !p.at(EOF) {
    p.error(template_expression_trailing_code(…));
    while !p.at(EOF) { p.bump_any(); }        // drain so EOF invariants hold
    expr_marker.complete(p, JS_BOGUS_EXPRESSION);
}
```

**Flow:** eat BOM/shebang → embedding forks (vue-handler → svelte-declaration → template-expression) → normal path: directives (strict-mode snapshot!) then Script vs Module body by `module_kind()`, `.d.ts` completing as declaration module → restore strict snapshot. Vue heuristic: try expression; accept as handler if EOF + whitelisted kind; function-ish kinds with trailing code drain+error; anything else rewinds to full script parse.
**Invariant:** The strict-mode snapshot from directives must be restored on EVERY exit path — it is taken before module-kind branching and restored after completion. Template roots always complete as `JS_EXPRESSION_TEMPLATE_ROOT` even when the child is bogus ("root should always be this type") so downstream tooling can rely on the shape. The rewind-on-mismatch keeps one parser binary serving all embeddings — no per-dialect grammars.
**Probe:** `crates/biome_js_parser/tests/js_test_suite/ok/{empty_object,arrow,binary,ternary}.inline_expr.js(.snap)` and `ok/ts_as.inline_expr.ts` (embedding-driven roots pinned via source-type-parameterized suite).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "biome", query: "parse vue event handler template expression svelte snippet root", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt source-type-predicate root dispatch with checkpoint-rewind fallback to the plain grammar; adapt embedding enums; omit dialect-specific node names.
