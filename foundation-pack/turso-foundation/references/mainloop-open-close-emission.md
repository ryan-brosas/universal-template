<!-- capsule-v2 -->
# Main-loop open/close emission — how does the planner turn a join order into nested bytecode loops?

**Source:** turso (Limbo) MIT `main@def9a060`; Codebase Memory project `turso`. **Question:** What per-table loop scaffolding (labels, match flags, rewind/last, deferred seeks, coroutine yields, anti-join anchors) must an emitter reproduce?

## OpenLoop/CloseLoop nested-loop emission
**Path/Symbol:** `core/translate/main_loop/open.rs:OpenLoop::emit` (:50, was :47 at `main@d9266124f`); `core/translate/main_loop/close.rs` (CloseLoop + `AutoIndexResult`); metadata structs in `core/translate/main_loop/mod.rs:LeftJoinMetadata/SemiAntiJoinMetadata/LoopLabels` (:73/:80/:87, was :95-123); anti-join chain fixup in open.rs :110-124 region.
**Signature:** `pub fn emit(program: &mut ProgramBuilder, t_ctx: &mut TranslateCtx, table_references: &TableReferences, join_order: &[JoinOrderMember], predicates: &[WhereTerm], temp_cursor_id: Option<CursorID>, mode: OperationMode, subqueries: &mut [NonFromClauseSubquery]) -> Result<()>`.
**Data Shape:** Per joined table: pre-allocated `LoopLabels { loop_start, next, loop_end }`; `meta_left_joins[idx] → LeftJoinMetadata { reg_match_flag, label_match_flag_set_true, label_match_flag_check_value }`; `meta_semi_anti_joins[idx] → SemiAntiJoinMetadata { label_body, label_next_outer, outer_table_idx }`.

### Decisive source
```rust
// core/translate/main_loop/open.rs — chained anti-joins relink the PREVIOUS body
if join_index > 0 {
    let prev_table_idx = join_order[join_index - 1].original_idx;
    let prev_is_anti = ...is_anti();
    if prev_is_anti {
        if let Some(prev_sa_meta) = t_ctx.meta_semi_anti_joins[prev_table_idx].as_ref() {
            program.preassign_label_to_next_insn(prev_sa_meta.label_body);
        }
    }
}
// Each OUTER JOIN has a "match flag" that is initially set to false ...
program.emit_insn(Insn::Integer { value: 0, dest: lj_meta.reg_match_flag });
// Scan::BTreeTable: Backwards => Last { pc_if_empty: loop_end } else Rewind
// then program.preassign_label_to_next_insn(loop_start);
// after opening both cursors:
program.emit_insn(Insn::DeferredSeek { index_cursor_id, table_cursor_id });
```
Search arms differ structurally: `Search::RowidEq` emits non-looping `SeekRowid { target_pc: next }`; `Search::Seek` may lazily build ephemeral auto-indexes via `emit_autoindex` (`AutoIndexResult { use_bloom_filter, .. }`). Subquery scans split on `QueryDestination::CoroutineYield` (InitCoroutine + Yield with `end_offset: loop_end`, FORWARDS-only asserted) vs `EphemeralTable` (Rewind/Last over materialized rows + `emit_materialized_subquery_result_columns`).

**Flow:** iterate join_order → resolve chained anti-join body anchor → zero outer match flags → resolve cursors → emit scan/search opener (Rewind/Last/VFilter/coroutine yield/SeekRowid) → preassign loop_start → DeferredSeek pairs index+table cursors. Close.rs mirrors with Next/Prev back-jumps; semi/anti joins override the "next" anchor to jump past body emission.
**Invariant:** Backwards iteration is only legal on materialized cursors — coroutine-backed subqueries assert FORWARDS ("cannot scan backwards"); the anti-join chain must re-anchor the previous body BEFORE emitting anything whose address could relocate it (body.rs repeats this rule at body entry: "otherwise relocated constants can make the backward jump land incorrectly").
**Probe:** text anchors: `grep -c 'preassign_label_to_next_insn(prev_sa_meta.label_body)' core/translate/main_loop/open.rs` → 1; `grep -c 'resolve_anti_join_entry' core/translate/main_loop/body.rs` → 2. Runner (gate-5 precedent from passes 8-11): any `cargo test -p turso_core --lib main_loop` subset compiles these modules at HEAD.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "turso", query: "OpenLoop emit LoopLabels LeftJoinMetadata", limit: 10 });
```

## Verdict
Adopt the label/metadata triad and the opener taxonomy (Rewind/Last vs VFilter vs coroutine vs SeekRowid), the DeferredSeek pairing, and the anti-join relink ladder. Adapt instruction mnemonics to host VM. Omit UPDATE-mode PrebuiltEphemeralTable special casing unless porting DML emission too.
