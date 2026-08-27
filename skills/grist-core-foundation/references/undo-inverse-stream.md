<!-- capsule-v2 -->
# Undo as inverse-action stream — how is the undo of a mixed action group derived without storing snapshots or inverting state?

**Source:** grist-core Apache-2.0 `main@c057666bb93b6f93a69b0884ce023676c3a2804b`; Codebase Memory `grist-core`. **Question:** Given one applied useraction that mixes stored edits and formula-produced calc updates, what exactly does Grist replay to undo it, and what correctness boundary does that have?

## Per-handler inverse append + reversed replay (docactions.py + engine.py)
**Path/Symbol:** `sandbox/grist/docactions.py:DocActions.*` (records :17–106, columns/tables :112–270 — every handler appends its inverse to out_actions.undo); `sandbox/grist/useractions.py:UserActions.ApplyUndoActions` (:343–345); `sandbox/grist/engine.py:_get_undo_checkpoint/_undo_to_checkpoint` (:1517–1543).
**Signature:** `ApplyUndoActions(undo_actions)` (a @useraction like any other); checkpoint tuple `(len(calc), len(stored), len(undo), len(retValues))`.
**Data Shape:** `out_actions.undo` is a plain list of Python action namedtuples parallel to stored; entries are pre-inverted single/bulk actions (via .simplify() collapse); removal inverses omit columns whose values were all default.

### Decisive source
```python
# docactions.BulkRemoveRecord — capture prior values while they still exist:
    undo_values = {}
    for column in table.all_columns.values():
      if not column.is_private() and column.col_id != "id":
        col_values = [column.raw_get(r) for r in row_ids]
        default = column.getdefault()
        # If this column had all default values, do not include it into the undo BulkAddRecord.
        if not all(strict_equal(val, default) for val in col_values):
          undo_values[column.col_id] = col_values
      for row_id in row_ids:
        column.unset(row_id)
    self._engine.out_actions.undo.append(
        actions.BulkAddRecord(table_id, row_ids, undo_values).simplify())

# useractions.ApplyUndoActions (:343-345) — undo is just another useraction:
  def ApplyUndoActions(self, undo_actions):
    for undo_action in reversed(undo_actions):
      self._do_doc_action(actions.action_from_repr(undo_action))

# engine._undo_to_checkpoint (:1530-1542) — trim self-produced undo tails:
      # ...applying any undo actions, and trim it back to original state (if we do not trim it, it
      # will only grow further, with undo actions themselves getting applied as new doc actions).
      self.user_actions.ApplyUndoActions([actions.get_action_repr(a) for a in undo_actions])
      del self.out_actions.calc[len_calc:]; del self.out_actions.stored[len_stored:]
      del self.out_actions.direct[len_stored:]; del self.out_actions.undo[len_undo:]
```
Schema inverses follow the same shape: AddColumn->RemoveColumn, RemoveColumn->AddColumn(saved col_info), RenameColumn->swapped rename, ModifyColumn->ModifyColumn(saved col_info), AddTable/RemoveTable/RenameTable likewise (docactions.py :112–270); useractions.py :1840–1846 patches the last ModifyColumn undo in place for conversions.

**Flow:** each applied doc-action handler pushes ONE exact inverse built from pre-change reads (prior raw cell values, old schema descriptors, whole-table snapshot for ReplaceTableData) onto out_actions.undo in application order -> the host later replays that array through ApplyUndoActions IN REVERSE (it is ordinary application: fully direct=True, formulas re-run, and the replay emits fresh calc updates plus NEW undo entries) -> inside a single apply_user_actions call, engine checkpoints roll back and TRIM undo tails produced by side effects or by undoing itself, preventing unbounded growth.
**Invariant:** undo is INVERSE-OF-HISTORY, not complement-of-state: replaying prior values through the live engine means deterministic formulas restore their old results, but NON-deterministic formulas drift (test_formula_undo counter reaches #8 instead of #6) — never promise bit-exact state restoration, and never let undo-generated undo entries accumulate past the current call.
**Probe:** `sandbox/grist/test_formula_undo.py::test_change_and_undo` (:11–93: stored+undo arrays asserted verbatim including calc updates; reversed replay asserted with direct=[True,...,False] marker).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "grist-core", query: "out_actions undo ApplyUndoActions inverse doc actions", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt per-handler inverse emission at write time plus reversed replay through the normal application path with checkpoint trimming — it needs no snapshots and no inversion algebra over mixed groups. Adapt where the undo list lives (host action history vs engine output); omit Grist direct-marker bookkeeping only if your host has no stored/calc distinction. Caveat: there is NO ReverseSingleActions/complement builder at this pin — older plans assuming computed complements are wrong for this source.
