<!-- capsule-v2 -->
# CFG if/else deferred join — how do you back-patch a branch's exit jump when the else clause parses after the then-body?

**Source:** biome MIT `main@6cd32636f463551b8dfe46aeefb1191d437b4694`; Codebase Memory `biome`. **Question:** How does an else clause mutate its parent if-statement's state mid-parse without breaking the visitor contract?

## IfVisitor / ElseVisitor cursor choreography
**Path/Symbol:** `crates/biome_js_analyze/src/services/control_flow/nodes/if_stmt.rs:IfVisitor` (:10-84), `ElseVisitor` (:86-123).
**Signature:** `IfVisitor { entry_block: BlockId, consequent_start: BlockId, consequent_end: Option<BlockId>, alt_block: Option<(BlockId, BlockId)> }`; `ElseVisitor { consequent_block: BlockId, alt_block: BlockId }`; `fn enter(node: JsIfStatement|JsElseClause, builder, stack) -> SyntaxResult<Self>`.
**Data Shape:** `consequent_end`/`alt_block` are `Option`s filled by ElseVisitor via `stack.read_top::<IfVisitor>()?`; when absent (no else) IfVisitor derives them from the live cursor.

### Decisive source
```rust
// if_stmt.rs:56-80 (exit) — teleport BACKWARD to entry to emit the test
// fork, forward through each arm to patch its join jump; the next_block
// join is allocated AFTER both arms exist
let next_block = builder.append_block();
builder.set_cursor(self.entry_block);
if let Some((alt_start, alt_end)) = alt_block {
    builder.append_jump(true, self.consequent_start).with_node(node.test()?.into_syntax());
    builder.append_jump(false, alt_start);
    builder.set_cursor(alt_end);
    builder.append_jump(false, next_block);
} else {
    builder.append_jump(true, self.consequent_start).with_node(node.test()?.into_syntax());
    builder.append_jump(false, next_block);
}
builder.set_cursor(consequent_end);   // unwrap_or(cursor) when no else
builder.append_jump(false, next_block);
builder.set_cursor(next_block);
```
```rust
// if_stmt.rs:99-102 + 116-119 — ElseVisitor::enter snapshots the then-end
// cursor BEFORE appending its own block, then writes it into the parent
let consequent_block = builder.cursor();
let alt_block = builder.append_block();
…
if_state.consequent_end = Some(self.consequent_block);
if_state.alt_block = Some((self.alt_block, builder.cursor()));
```

**Flow:** IfVisitor::enter saves entry cursor, allocates consequent, parks cursor there → then-body appends → ElseVisitor::enter snapshots body-end, allocates alternate, parks → else-body appends → ElseVisitor::exit writes both ids into the parent frame on the stack → IfVisitor::exit allocates next and back-patches: entry{test?→consequent : →(alt|next)}, alt-end→next, consequent-end→next.
**Invariant:** The conditional Jump is emitted in exit (not enter) so `.with_node(test)` can attach the real syntax node once parsing has confirmed it exists. Without an else, "consequent end" = wherever the cursor sits at if-exit. Every arm terminates with exactly one explicit jump to next — no fallthrough duplication.
**Probe:** `crates/biome_js_analyze/tests/specs/correctness/noUnreachable/JsIfStatement.js(+.snap)` plus nested-if fixtures in the same suite.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "biome", query: "ElseVisitor", limit: 10, fields: ["signature", "name", "file"] });
```
**Verdict:** Adopt parent-frame mutation via read_top + backward-teleport emit verbatim. Adapt node/test accessors. Omit nothing.
