<!-- capsule-v2 -->
# CFG try/catch block topology — in what order must try regions allocate blocks, and where do the implicit jumps go?

**Source:** biome MIT `main@6cd32636f463551b8dfe46aeefb1191d437b4694`; Codebase Memory `biome`. **Question:** How do you wire next/finally/catch/try blocks so completion paths route through finally exactly once?

## TryVisitor / CatchVisitor / FinallyVisitor choreography
**Path/Symbol:** `crates/biome_js_analyze/src/services/control_flow/nodes/try_catch.rs` (TryVisitor :10-59, CatchVisitor :61-103, FinallyVisitor :105-152).
**Signature:** `TryVisitor { catch_block: Option<BlockId>, finally_block: Option<BlockId>, next_block: BlockId }`; `fn enter(node: AnyJsTryStatement, builder: &mut FunctionBuilder, _: StatementStack) -> SyntaxResult<Self>`; CatchVisitor/FinallyVisitor are unit structs whose `enter/exit` mutate the builder + read `stack.read_top::<TryVisitor>()`.
**Data Shape:** `AnyJsTryStatement = JsTryStatement | JsTryFinallyStatement`; `has_catch` for try-finally comes from `node.catch_clause().is_some()`.

### Decisive source
```rust
// try_catch.rs:29-51 — allocation ORDER is load-bearing: next → finally →
// catch → try. Only try_block is created while BOTH targets are pushed,
// so only it snapshots both handlers (see cfg-exception-handler-snapshot).
let next_block = builder.append_block();
let finally_block = if has_finally { …push_exception_target(Finally, …) } else { None };
let catch_block   = if has_catch    { …push_exception_target(Catch, …)    } else { None };
// Create the actual try block (with the exception target set), append
// an implicit jump to it and move the cursor there
let try_block = builder.append_block();
builder.append_jump(false, try_block);
builder.set_cursor(try_block);
```
```rust
// try_catch.rs:73-82 — entering catch closes the try region with an implicit
// jump to finally-or-next, THEN pops the catch handler off the stack
builder.append_jump(false, try_stmt.finally_block.unwrap_or(try_stmt.next_block));
builder.pop_exception_target();
builder.set_cursor(try_stmt.catch_block.unwrap());
```

**Flow:** enter allocates 4 blocks and pushes targets → body statements append into `try_block` → `CatchVisitor::enter`: implicit jump end-of-try→(finally|next), pop Catch, cursor→catch_block; its exit adds jump catch→(finally|next) → `FinallyVisitor::enter` (no-catch case): jump try-end→finally + cursor→finally, then pops Finally; exit emits `append_finally_fallthrough(next)` — a Jump with `finally_fallthrough:true` so unwinding may retarget it to the NEXT outer handler — and parks the cursor on next.
**Invariant:** Every normal completion path lands on finally exactly once via explicit jumps; throw paths reach it via exception edges. The pops happen at CLAUSE boundaries, not try-exit — code after the whole statement runs with both handlers popped. A porter who pops in TryVisitor::exit instead double-pops nothing but mis-scopes any sibling statements parsed inside.
**Probe:** `crates/biome_js_analyze/tests/specs/correctness/noUnreachable/*.js(+.snap)` fixtures cover try/finally reachability; upstream also snapshot-tests CFG printing via insta (`crates/biome_js_analyze/tests/specs_analysis/…control_flow…` snapshots exist for debug output). Coverage caveat: no dedicated unit tests for this file.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "biome", query: "FinallyVisitor", limit: 10, fields: ["signature", "name", "file"] });
```
**Verdict:** Adopt allocation order + clause-boundary pops + finally_fallthrough semantics verbatim. Adapt to your AST's try-shape union. Omit nothing.
