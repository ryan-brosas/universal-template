<!-- capsule-v2 -->
# Delete-operator event rewriting — how do you validate an expression *after* parsing it, without re-parsing?

**Source:** Biome MIT `main@6cd32636f463551b8dfe46aeefb1191d437b4694`; Codebase Memory `biome`. **Question:** How can a parser enforce "delete target may not be an identifier or private member" when the violation is only visible once the operand is fully parsed?

## DeleteExpressionRewriter + rewrite_events
**Path/Symbol:** `crates/biome_js_parser/src/syntax/expr.rs:DeleteExpressionRewriter` (:2081-2124), consumer call site (:2043-2075); machinery: `crates/biome_js_parser/src/rewrite.rs` (`rewrite_events`), `crates/biome_js_parser/src/parser/rewrite_parser.rs:RewriteParser` (1-162).
**Signature:** `impl RewriteParseEvents for DeleteExpressionRewriter { fn start_node(&mut self, kind, p: &mut RewriteParser); fn finish_node(&mut self, p: &mut RewriteParser); }`; `rewrite_events(&mut rewriter, checkpoint, p)`.
**Data Shape:** Rewriter state: `stack: Vec<(RewriteMarker, JsSyntaxKind)>`, `result: Option<CompletedMarker>`, and three "just exited" latches: `exited_ident_expr: Option<TextRange>`, `exited_private_name: bool`, `exited_private_member_expr: Option<TextRange>`.

### Decisive source
```rust
fn finish_node(&mut self, p: &mut RewriteParser) {
    let (m, kind) = self.stack.pop().expect("stack depth mismatch");
    let node = m.complete(p, kind);
    if kind != JS_PARENTHESIZED_EXPRESSION && kind != JS_SEQUENCE_EXPRESSION {
        self.exited_private_member_expr = if self.exited_private_name && kind == JS_STATIC_MEMBER_EXPRESSION { Some(node.range(p)) } else { None };
        self.exited_ident_expr = if kind == JS_IDENTIFIER_EXPRESSION { Some(node.range(p)) } else { None };
        self.exited_private_name = kind == JS_PRIVATE_NAME;
    }
    self.result = Some(node.into());
}
```

**Flow:** parse the unary operand normally into a checkpoint range → `rewrite_events` replays Start/Token/Finish events through `RewriteParser`, which pushes **tombstone events** for re-emitted nodes and re-creates markers with explicit offsets → the rewriter rebuilds the node tree while tracking what was just exited → after replay, `rewriter.result` plus the latches decide `JS_UNARY_EXPRESSION` vs `JS_BOGUS_EXPRESSION` + diagnostics.
**Invariant:** Parenthesized and sequence expressions are transparent — exiting them must NOT reset the latches (`delete (obj.#member).key` stays flagged; `delete (a)` still errors on the identifier inside). `RewriteParser` deliberately does not use the TokenSource for positions: rewinding during replay would re-lex template-literal tokens in the wrong `JsLexContext`, so it tracks a raw byte offset and skips trivia from the pre-computed trivia list instead.
**Probe:** `crates/biome_js_parser/tests/js_test_suite/error/unary_delete.js` + `unary_delete_parenthesized.js` (the parenthesized-transparency matrix, ~40 cases).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "biome", query: "RewriteParseEvents rewrite_events tombstone", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt post-parse event replay as the answer to any "rule depends on the finished subtree" problem in a parser (also usable for AST-level lint checks at parse time); adapt latch conditions to your rule set; omit Biome's specific delete rules. The detached-offset RewriteParser trick is mandatory wherever replay rewinds.
