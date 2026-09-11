<!-- capsule-v2 -->
# Exception/cleanup handler snapshot — when do try/finally edges attach to CFG blocks?

**Source:** biome MIT `main@6cd32636f463551b8dfe46aeefb1191d437b4694`; Codebase Memory `biome`. **Question:** At what moment does a block learn which catch/finally handlers guard it, and why can't a porter resolve them later?

## Allocation-time handler capture from the exception stack
**Path/Symbol:** `crates/biome_control_flow/src/builder.rs:FunctionBuilder.append_block` (:52-85), `push_exception_target`/`pop_exception_target` (:101-109); consumers: `crates/biome_js_analyze/src/services/control_flow/nodes/try_catch.rs:TryVisitor.enter` (:19-58).
**Signature:** `fn append_block(&mut self) -> BlockId`; `pub fn push_exception_target(&mut self, kind: ExceptionHandlerKind, target: BlockId)`; `pub fn pop_exception_target(&mut self)`.
**Data Shape:** builder field `exception_target: Vec<ExceptionHandler>` = stack of `{kind: Catch|Finally, target: BlockId}`; each new block gets `exception_handlers` (catches + finallys up to first Catch, reversed to innermost-first) and `cleanup_handlers` (all Finallys on the stack).

### Decisive source
```rust
// builder.rs:60-82 — handlers are SNAPSHOTTED from the exception stack at the
// instant the block is allocated; they are never recomputed afterwards
let mut has_catch_handler = false;
self.result.blocks.push(BasicBlock::new(
    // The exception handlers for a block are all the handlers in the
    // current exception stack up to the first catch handler
    self.exception_target.iter().rev().copied().take_while(|handler| {
        let has_previous_catch = has_catch_handler;
        has_catch_handler |= matches!(handler.kind, ExceptionHandlerKind::Catch);
        !has_previous_catch
    }),
    // The cleanup handlers for a block are all the handlers in the
    // current exception stack with the catch handlers filtered out
    self.exception_target.iter().rev().filter_map(|handler| match handler.kind {
        ExceptionHandlerKind::Finally => Some(*handler),
        ExceptionHandlerKind::Catch => None,
    }),
));
```

**Flow:** `TryVisitor::enter` pushes targets in a fixed order — allocate `next`, then (if finally) push `(Finally, finally_block)` allocating it, then (if catch) push `(Catch, catch_block)` allocating it, then allocate `try_block` LAST so only the try body snapshots both handlers → nested trys stack deeper entries → `CatchVisitor::enter` / `FinallyVisitor::enter` `pop_exception_target()` as their region ends → blocks created after the pop (catch body itself, code after the try) carry the outer handlers only.
**Invariant:** Handler membership is frozen at allocation; there is no post-hoc edge patching. A porter who allocates the try-body block BEFORE pushing targets gets a try block with NO exception edges — silently wrong graphs. Corollary: any block created between push and pop inherits those handlers, which is exactly how the implicit jump out of a loop body inside a try still routes through finally. `finally_fallthrough` jumps (`append_finally_fallthrough`, :138-144, sets `Jump.finally_fallthrough=true`) let unwinding reinterpret the fallthrough target as the next outer exception handler.
**Probe:** No unit tests in `biome_control_flow`; pinned by fixtures consuming handler lists: `crates/biome_js_analyze/tests/specs/correctness/noUnreachable/JsBreakStatement.js(+.snap)` (break out of try/finally) and `useIterableCallbackReturn`-style suites; complexity scoring in `crates/biome_js_analyze/src/lint/correctness/no_unreachable.rs:215-240` counts side-effecting statements × handler-list lengths, proving handlers are per-block data.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "biome", query: "push_exception_target", limit: 10, fields: ["signature", "name", "file"] });
```
**Verdict:** Adopt snapshot-at-allocation + fixed next→finally→catch→try creation order verbatim. Adapt handler kinds to your language's unwind taxonomy. Omit nothing here — this is the load-bearing half of the crate.
