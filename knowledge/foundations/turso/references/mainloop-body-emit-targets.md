<!-- capsule-v2 -->
# Loop body emit-target ladder — where do rows from the innermost join loop go?

**Source:** turso (Limbo) MIT `main@def9a060`; Codebase Memory project `turso`. **Question:** How does the emitter decide between GROUP BY / AggStep / Window / ORDER-BY-sorter / raw-result row sinks, and what does each emit?

## LoopEmitTarget selection + per-target emission
**Path/Symbol:** `core/translate/main_loop/body.rs:LoopBodyEmitter::emit` (:52, was :60 at `main@d9266124f`), `select_emit_target` (:95, was :100), `emit_loop_source` (:131, was :129); doc comment :14-24.
**Signature:** `fn select_emit_target(&self) -> LoopEmitTarget` (private; precedence fixed by if-chain).
**Data Shape:** enum `LoopEmitTarget { GroupBy, OrderBySorter, AggStep, Window, QueryResult }`; group-by path reads `GroupByMetadata { row_source: GroupByRowSource::{Sorter{sort_cursor, sorter_column_count, reg_sorter_key, ..}, MainLoop{..}}, registers, .. }`.

### Decisive source
```rust
// core/translate/main_loop/body.rs — precedence IS the contract
if self.plan.group_by.as_ref().is_some_and(|gb| !gb.exprs.is_empty()) {
    return LoopEmitTarget::GroupBy;
}
if !self.plan.aggregates.is_empty() { return LoopEmitTarget::AggStep; }
if self.plan.window.is_some()       { return LoopEmitTarget::Window; }
if !self.plan.order_by.is_empty()   { return LoopEmitTarget::OrderBySorter; }
LoopEmitTarget::QueryResult
```
GroupBy/sorter arm: translate non-aggregate expressions in order (GROUP BY keys first, then remaining non-aggregates); sorter rowsource stores ONLY unique leaf columns of aggregate args ("Full expressions are re-evaluated from the pseudo cursor during aggregation") then `sorter_insert(...)`; MainLoop rowsource instead translates every aggregate's args and calls `group_by_agg_phase`. AggStep arm handles simple Min/Max with an ascending-index NULL-skip label ("Ascending index order places NULLs first... jump straight to AggFinal"), FILTER-clause skip labels per aggregate, and deliberately does NOT evaluate outer expressions containing aggregates (accumulators first; composite expressions evaluated at AggFinal time).

**Flow:** resolve_anti_join_entry FIRST (preassign last anti-join body before choosing target) → select target by ladder → emit sink-specific register traffic. Distinct ORDER-BY inserts preassign `distinct_ctx.label_on_conflict` after the sorter insert.
**Invariant:** The ladder order is semantic, not stylistic: a query with both GROUP BY and ORDER BY must feed the GROUP BY sorter (ordering handled downstream); skipping the anti-join preassignment corrupts jump targets when constant relocation shifts instruction addresses.
**Probe:** text anchors: `grep -c 'LoopEmitTarget::GroupBy => {' core/translate/main_loop/body.rs` → 1; `grep -c 'resolve_anti_join_entry' core/translate/main_loop/body.rs` → 2. Direct tests live in the translate suite (`cargo test -p turso_core --lib main_loop`, runner-gated as in passes 8-11).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "turso", query: "emit_loop_source LoopEmitTarget GroupByRowSource", limit: 10 });
```

## Verdict
Adopt the five-target ladder and the two GroupBy rowsources (sorter stores leaf columns only; main-loop re-aggregates in place). Adapt register allocation to host builder API. Omit window-function internals (`core/window`) — separate plane.
