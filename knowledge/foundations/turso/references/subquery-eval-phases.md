<!-- capsule-v2 -->
# Subquery eval-phase assignment — when does each non-FROM subquery actually run?

**Source:** turso (Limbo) MIT `main@def9a060`; Codebase Memory project `turso`. **Question:** How are evaluation phases chosen for scalar/EXISTS/IN subqueries so no subquery runs before its dependencies (or after its first use)?

## assign_select_subquery_eval_phases + phase floors
**Path/Symbol:** `core/translate/subquery.rs::assign_select_subquery_eval_phases` (:2100, drift-shifted from :2173 at `main@d9266124f`; issue-#6807 floor comment :2110) with helpers `subquery_reads_outer_aggregate` (:2188, was :2263), `expr_reads_subquery` (:2165, was :2243); clause-order planning in `plan_subqueries_from_select_plan` (:234, was :236, WHERE→GROUP BY→HAVING→result columns→ORDER BY→LIMIT/OFFSET); floor table `core/translate/plan.rs::SubqueryOrigin::phase_floor` (:339, was :338).
**Signature:** `fn assign_select_subquery_eval_phases(plan: &mut SelectPlan)`; enum `SubqueryEvalPhase` (BeforeLoop / PreWrite / PostWriteReturning / GroupedOutput / UngroupedAggregateOutput).
**Data Shape:** each `NonFromClauseSubquery` gets an `eval_phase: SubqueryEvalPhase`; result columns may be re-flagged `contains_aggregates = true` as a deferral marker.

### Decisive source
```rust
// subquery.rs:2177-2181 — the phase-floor exception (#6807)
// Subqueries inside an aggregate's arguments or FILTER clause are evaluated
// per input row by the aggregate step code in the main loop, even when the
// aggregate itself belongs to HAVING or ORDER BY. Deferring them to the
// grouped output subroutine would emit their materialization AFTER their
// first use, so they must keep their phase floor (issue #6807).
// plan.rs:355-357 — DML floors differ from SELECT:
SubqueryOrigin::DmlSet => SubqueryEvalPhase::PreWrite,
SubqueryOrigin::DmlReturning => SubqueryEvalPhase::PostWriteReturning,
```

**Flow:** all non-FROM subqueries are planned in clause order (LIMIT/OFFSET pass uses a closure returning NO outer refs — they can never be correlated :364-391; a CSE map dedupes scalar subqueries shared between GROUP BY and the SELECT list :242-267) → phases assigned: subquery reading an OUTER aggregate ⇒ GroupedOutput (grouped queries) or UngroupedAggregateOutput; HAVING/ORDER BY origins in grouped queries ⇒ GroupedOutput UNLESS the subquery sits inside an aggregate's args/FILTER (keep floor); everything else keeps its origin floor → finally, any plain result column READING such an output-phase subquery is marked `contains_aggregates` so the emitter defers it instead of taking an arbitrary row's NULL mid-scan.
**Invariant:** the binding constraint is emit-before-first-use within the main loop: aggregates' inner subqueries are consumed PER INPUT ROW, which is EARLIER than GroupedOutput — so origin-based deferral would materialize too late. The mirror rule: a subquery that reads an aggregate the OUTER query finalizes must run at or after the aggregate-output phase, or its read register is still NULL. Aggregates are RE-COLLECTED after subquery planning because EXISTS→SubqueryResult rewriting leaves stale args and cleared ORDER BYs orphan aggregates (:393-403).
**Probe:** text anchors: `grep -c 'issue #6807' core/translate/subquery.rs` → 1; `grep -c 'DmlReturning => SubqueryEvalPhase::PostWriteReturning' core/translate/plan.rs` → 1; `grep -c 'subquery_reads_outer_aggregate' core/translate/subquery.rs` → 2; behavior covered by query_processing integration suites (`tests/integration/query_processing/`) driving grouped/aggregate queries end-to-end.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "turso", query: "assign_select_subquery_eval_phases SubqueryEvalPhase phase_floor", limit: 10 });
```

## Verdict
Adopt the phase-floor-with-exception model and the contains_aggregates deferral marker for outer-aggregate readers; adapt phase names to your emitter's pipeline stages; omit the stack-trace instrumentation macros.
