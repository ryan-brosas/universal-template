<!-- capsule-v2 -->
# EQP detail vocabulary — how do you emit EXPLAIN QUERY PLAN rows that mean what SQLite users expect?

**Source:** turso (MIT) `main@d9266124f` (/mnt/hdd/utopia/inspo/memory/turso); Codebase Memory `turso`. **Question:** What closed set of plan details covers every row source, and where does the end-key operator get REVERSED for display?

## One enum, one Display, and the SeekOp negation rule
**Path/Symbol:** `core/translate/eqp.rs`: `EqpDetail` (:214-295), `Display for EqpDetail` (:298-385), `seek_constraint_parts` (:389-425), `EqpSearchKind/EqpSortMethod/EqpCompoundOp/EqpJoin/EqpSubqueryExec` (:163-211), `program_plan_json` (:804+).
**Signature:** `pub(crate) fn seek_constraint_parts(index: &Index, seek_def: &SeekDef) -> Vec<String>`; `pub(crate) fn eqp_detail_for_table_op(table: &JoinedTable, join: Option<EqpJoin>, subquery: Option<EqpSubquery>) -> EqpDetail`.
**Data Shape:** 17-variant enum: ConstantRow / Scan{table,index,source,backwards,join,subquery} / Search{table,kind,index,constraints,backwards,join,subquery} / MultiIndex{union} / IndexMethod{method} / HashJoin / HashBuild / Distinct / DistinctAggregate{function} / OrderBy{method: TempBTree|Sorter} / GroupBy / Compound / CompoundArm{op,temp_btree} / ListSubquery{id,correlated} / ScalarSubquery{id,correlated} / RecursiveSetup / RecursiveStep. Strings mirror sqlite3 EXPLAIN QUERY PLAN exactly: "SCAN t USING COVERING INDEX i", "SEARCH x USING INTEGER PRIMARY KEY (y=?)", "MULTI-INDEX OR x (i1, i2)", "QUERY INDEX METHOD m", "MATERIALIZE hash build input for t", "USE HASH TABLE FOR count(DISTINCT)", "CORRELATED LIST SUBQUERY 2", "LEFT-JOIN" suffix.

### Decisive source
```rust
// eqp.rs:410-423 — the reversal trap (verbatim):
// Range constraint from end key.
// The end key's SeekOp is the B-tree termination condition (the negation of the
// user-facing SQL operator), so we reverse it for display.
if let SeekKeyComponent::Expr(_) = &seek_def.end.last_component {
    if let Some(col) = index.columns.get(range_col_idx) {
        let op_str = match seek_def.end.op {
            SeekOp::GE { .. } => "<",
            SeekOp::GT => "<=",
            SeekOp::LE { .. } => ">",
            SeekOp::LT => ">=",
        };
        parts.push(format!("{}{op_str}?", col.name));
    }
}
```

**Flow:** planner builds JoinedTable ops → eqp_detail_for_table_op maps Operation→detail (Scan picks up covering-index + backwards from IterationDirection) → constraints render as `col=?` equality prefix plus range arm(s); START key op displays AS-IS (`>=`,`>`,`<=`,`<`), END key op displays NEGATED because the stored SeekOp is the btree STOP condition → Display prints the canonical string; JSON mode (program_plan_json) emits the same tree via a hand-rolled JsonBuilder with json_escape_into.
**Invariant:** the display vocabulary is a COMPATIBILITY SURFACE — scripts parse these exact strings — so new row sources must map into existing wording (e.g. IndexMethod renders "QUERY INDEX METHOD <name>") rather than invent phrasing. The end-op negation is invisible in single-sided ranges but produces wrong output on every BETWEEN-style seek if a porter copies start-op rendering to the end arm.
**Probe:** `grep -n 'negation of the' core/translate/eqp.rs` hits :412; `grep -c 'write!(f' core/translate/eqp.rs` ≥ 15 in Display; behavior pinned by EXPLAIN QUERY PLAN sqllogic assertions under testing/ (eqp rows compared verbatim against expected strings).
**Retrieve:** search_graph "EqpDetail seek_constraint_parts program_plan_json" resolves `turso.core.translate.eqp.EqpDetail` core/translate/eqp.rs :214-295 line-exact.

## Verdict
Adopt the enum+Display split with the end-key operator negation as the porting core. Adapt variant set to your row sources but keep SQLite-compatible strings for the shared ones. Omit the JSON builder unless your EXPLAIN needs machine output. Coverage: no_recorded_issue on eqp.rs.
