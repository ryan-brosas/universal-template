<!-- capsule-v2 -->
# CFG visitor orchestrator — how does a merged visitor stack drive one FunctionBuilder per function without cross-function leakage?

**Source:** biome MIT `main@6cd32636f463551b8dfe46aeefb1191d437b4694`; Codebase Memory `biome`. **Question:** How are per-statement visitor states stacked, scoped to the enclosing function, and kept type-safe across a macro-merged visitor?

## declare_visitor! macro + StatementStack slicing
**Path/Symbol:** `crates/biome_js_analyze/src/services/control_flow/visitor.rs:declare_visitor!` (:23-106), `ControlFlowVisitor` table (:108-131), `FunctionVisitor` (:158-198), `VisitorAdapter` (:218-273), `AnyJsControlFlowRoot` union (:162-176); service wiring `crates/biome_js_analyze/src/services/control_flow.rs:16-40`.
**Signature:** `StatementStack<'a> { stack: &'a mut [(TypeId, usize)], … }`; `fn new(visitor: &'a mut $name) -> Option<(&'a mut FunctionVisitor, Self)>`; trait `MergedVisitor { fn read_top(self) -> SyntaxResult<&mut N>; fn try_downcast(&self, TypeId, usize) -> Option<&N> }`; adapter `fn enter(node, ctx, stack) -> VisitorAdapter<V>` where `V: NodeVisitor { fn enter(node, &mut FunctionBuilder, StatementStack) -> SyntaxResult<Self>; fn exit(...) }`.
**Data Shape:** merged visitor holds one parallel slot-list per node-kind visitor (`visitor.$id: Vec<(usize, VisitorAdapter<V>)>` — outer stack position + inner index into that kind's list) plus a single global `stack: Vec<(TypeId, usize)>` of frames; `FunctionVisitor { builder: Option<FunctionBuilder> }`.

### Decisive source
```rust
// visitor.rs:46-53 — slice the shared state at the TOPMOST function frame;
// everything below belongs to enclosing functions and is out of scope
let (index, builder) = visitor.function.last_mut()?;
Some((builder, Self {
    stack: visitor.stack.get_mut(*index + 1..)
        .unwrap_or_else(|| panic!("stack index out of bounds…")),
    // debug builds additionally cut each per-kind list below *index
```
```rust
// visitor.rs:236-244 — ERROR POISONING: any enter() error takes the builder,
// so every subsequent statement in this function becomes a no-op
let result = if let Some(builder) = visitor.builder.as_mut() {
    let result = V::enter(node, builder, stack);
    if result.is_err() { visitor.builder.take(); }
    result
}
```

**Flow:** `build_visitor` registers the merged visitor in `Phases::Syntax` (control_flow.rs:33-34) → `FunctionVisitor::enter` creates a `FunctionBuilder` for any control-flow root (module/script/functions/object+class members/static blocks/TsModuleDeclaration/TsPropertySignatureTypeMember) → nested statements push typed frames; `read_top::<V>()` reads the nearest same-kind frame; `try_downcast` resolves a `(TypeId, usize)` pair → on root exit `ctx.match_query(ControlFlowGraph{graph})` publishes the graph.
**Invariant:** The poisoned-builder protocol is fail-closed: after ANY error the whole function yields NO graph (rules see no query match), never a partial graph — a porter who "recovers" instead will emit garbage reachability results. `take_while(TypeId != FunctionVisitor)` in break/continue scans means jumps can NEVER target another function's labels. Debug-only per-kind offset slices exist solely to make cross-function frame access panic loudly.
**Probe:** No direct unit tests; behavior pinned by `crates/biome_js_analyze/tests/specs/correctness/noUnreachable/issue-3654.js(+.snap)` and the full 23-fixture suite (one graph per function body).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "biome", query: "FunctionVisitor", limit: 10, fields: ["signature", "name", "file"] });
```
**Verdict:** Adopt the two-level (TypeId,usize) frame indexing and poisoning contract verbatim. Adapt the visitor table to your grammar's node kinds. Omit the `#[cfg(debug_assertions)]` instrumentation if your port has no debug harness (but keep the semantics).
