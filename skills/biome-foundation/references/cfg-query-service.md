<!-- capsule-v2 -->
# CFG-as-query service — how does a per-function graph reach rules through the analyzer's query system?

**Source:** biome MIT `main@6cd32636f463551b8dfe46aeefb1191d437b4694`; Codebase Memory `biome`. **Question:** How is an expensive derived structure (a whole-function CFG) exposed to many rules without each rule rebuilding it?

## ControlFlowGraph QueryMatch/Queryable wiring
**Path/Symbol:** `crates/biome_js_analyze/src/services/control_flow.rs` (type aliases :5-7, `pub struct ControlFlowGraph` :16-19, `impl Queryable` :26-40); publisher `services/control_flow/visitor.rs:FunctionVisitor.exit` (:191-198).
**Signature:** `impl QueryMatch for ControlFlowGraph { fn text_range(&self) -> TextRange }`; `impl Queryable for ControlFlowGraph { type Input = Self; type Output = JsControlFlowGraph; type Services = (); fn build_visitor(analyzer, _) { analyzer.add_visitor(Phases::Syntax, make_visitor) } fn unwrap_match(_: &ServiceBag, query: &Self) -> Self::Output { query.graph.clone() } }`.
**Data Shape:** `JsControlFlowGraph = biome_control_flow::ControlFlowGraph<JsLanguage>`; the query object WRAPS the graph and re-publishes it via clone on every rule's `ctx.query()`.

### Decisive source
```rust
// control_flow.rs:26-40 — the service pattern: build once in a Syntax-phase
// visitor, publish as a query match, hand clones to any rule that declares
// type Query = ControlFlowGraph
fn build_visitor(analyzer: &mut impl AddVisitor<JsLanguage>, _: &AnyJsRoot) {
    analyzer.add_visitor(Phases::Syntax, make_visitor);
}
fn unwrap_match(_: &ServiceBag, query: &Self) -> Self::Output {
    query.graph.clone()
}
```

**Flow:** FunctionVisitor::exit publishes `ControlFlowGraph{graph}` per function → analyzer stores it in the ServiceBag keyed by text range → each consumer rule (`no_unreachable`, `no_unreachable_super`, `use_getter_return`, `use_iterable_callback_return`, `no_fallthrough_switch_clause`) declares `type Query = ControlFlowGraph` and receives `unwrap_match` output.
**Invariant:** The graph is built in `Phases::Syntax` — BEFORE semantic phases — so CFG consumers must not require semantic services. `graph.clone()` per unwrap is deliberate cheap-clone economics (Vec-of-instructions clone beats cross-rule caching complexity at this size). A porter who builds CFGs lazily inside each rule pays N× parse-tree walks instead of 1.
**Probe:** Consumer rules' fixture suites double as integration tests: `crates/biome_js_analyze/tests/specs/correctness/noUnreachable/*.js(+.snap)` (23 fixtures) and `crates/biome_js_analyze/tests/specs/correctness/noUnreachableSuper/{duplicateSuper,missingSuper,thisBeforeSuper}.js(+.snap)`.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "biome", query: "ControlFlowGraph", limit: 10, fields: ["signature", "name", "file"] });
```
**Verdict:** Adopt the build-once/publish-as-query pattern verbatim for any expensive derived IR. Adapt the query type name and phase to your analyzer's lifecycle. Omit the mermaid debug Display.
