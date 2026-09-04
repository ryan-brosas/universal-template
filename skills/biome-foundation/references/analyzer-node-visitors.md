<!-- capsule-v2 -->
# merge_node_visitors — how do transient per-node visitor states survive a shared traversal without cross-talk?

**Source:** Biome MIT `main@6cd32636f463551b8dfe46aeefb1191d437b4694`; Codebase Memory `biome`. **Question:** several node-specific visitors (if/try/loop handlers) must each keep state only for nodes currently on the stack — what two-index bookkeeping makes enter/exit pairing exact even across function boundaries?

## The visitor-merge seam
**Path/Symbol:** `crates/biome_analyze/src/visitor.rs` — `Visitor` trait (:49-61), `NodeVisitor` (:71-86), `merge_node_visitors!` macro (:121-182), `VisitorContext` (:11-38).
**Signature:** `fn enter(node: Self::Node, ctx: &mut VisitorContext<NodeLanguage<Self::Node>>, stack: &mut V) -> Self; fn exit(self, node, ctx, stack)`; generated struct holds `stack: Vec<(TypeId, usize)>` plus one `$id: Vec<(usize, $visitor)>` per member.
**Data Shape:** TWO parallel stacks: the shared `stack` records `(visitor TypeId, index into that visitor's own Vec)` for every entered node; each member Vec stores `(stack_index, state)` so either side can find its partner. This is the SAME `(TypeId, usize)` scheme the js_analyze control-flow `StatementStack` uses to slice at the topmost function frame.

### Decisive source
```rust
// visitor.rs:150-161 (Enter) and 167-176 (Leave) — the return-on-first-cast is
// load-bearing: a node is handled by AT MOST ONE member visitor.
WalkEvent::Enter(node) => {
    let kind = node.kind();
    $(
        if <$visitor::Node as AstNode>::can_cast(kind) {
            let node = ...unwrap_cast(node.clone());
            let state = <$visitor>::enter(node, &mut ctx, self);
            let stack_index = self.stack.len();
            let ty_index = self.$id.len();
            self.$id.push((stack_index, state));
            self.stack.push((TypeId::of::<$visitor>(), ty_index));
            return;                       // <- first match wins, no fall-through
        }
    )*
}
WalkEvent::Leave(node) => {
    // pop from BOTH stacks before calling exit, then exit(state, node, ...)
    self.stack.pop().unwrap();
    let (_, state) = self.$id.pop().unwrap();
    ...
}
```
**Flow:** every Enter tries members in declaration order; the winner allocates its state, pushes both indices, returns. Leave mirrors: pop shared stack, pop member vec, run `exit`. Because pops happen BEFORE exit runs, an exit that pushes queries or signals cannot see its own frame again; because indices are stored in BOTH directions, a member's exit can inspect ancestors via the shared stack (the control-flow visitors' `read_top` trick). Visitors receive a fresh `VisitorContext` per event carrying phase, root, services, range filter, query_matcher, signal_queue, suppression_action, options (:11-20); `push_signal` bypasses rule dispatch entirely (:35-37). The default `Visitor::finish` is a no-op receiving `VisitorFinishContext { root, services: &mut ServiceBag }`.
**Invariant:** enter/exit pairing is structural — a member's states are strictly LIFO within one traversal; if `enter` panics after pushing, the stacks desynchronize (no drop guard) — porters adding fallible enters need unwind safety; node types claimable by two members resolve to the FIRST listed member silently.
**Probe:** `crates/biome_analyze/src/syntax.rs` test `syntax_visitor` :126-217 pins the plain-Visitor path end-to-end (exact kinds sequence ROOT → EXPRESSION_LIST → LITERAL ×2); the macro itself has no unit test — its consumers in `biome_js_analyze/src/services/control_flow/nodes/*.rs` (16 handlers, all pass-7 capsules) are the behavioral pin.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "biome", query: "NodeVisitor VisitorContext VisitorFinishContext", limit: 10, fields: ["signature", "name", "file"] });
// NodeVisitor visitor.rs 71-86; VisitorContext 11-20; syntax.Ast.build_visitor syntax.rs 22-27 (line-exact)
```

## Verdict
Adopt the two-stack (TypeId,index)↔(index,state) merge pattern for any multi-node-state traversal, the first-match-wins cast ladder, and context-per-event plumbing; adapt member sets per language; omit the UnionLanguage type-level join unless you also merge heterogeneous languages. Coverage caveat: pinned indirectly through the control-flow consumer suite rather than a direct macro test.
