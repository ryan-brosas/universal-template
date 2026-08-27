<!-- capsule-v2 -->
# Trigger-formula recalc gating — which data edits trigger dependent recalculation under which RecalcWhen modes?

**Source:** grist-core Apache-2.0 `main@c057666bb93b6f93a69b0884ce023676c3a2804b`; Codebase Memory `grist-core`. **Question:** When a user sets an explicit value or edits a data field, exactly when does a data column that carries a formula (trigger formula) get recomputed, and how are explicit values protected from immediate overwrite?

## prevent_recalc + RecalcWhen consumer ladder
**Path/Symbol:** `sandbox/grist/schema.py:RecalcWhen` (:386–394); `sandbox/grist/useractions.py:UserActions.doBulkUpdateRecord` gating tail (:573–590); `sandbox/grist/docactions.py:DocActions.BulkUpdateRecord` (:68–99, explicit-value prevention :82–86, metadata-change hook :96–99); `sandbox/grist/engine.py:prevent_recalc` (:1120–1125), `_maybe_update_trigger_dependencies` (:1211–1238), `invalidate_column` tail (:1115–1118).
**Signature:** `prevent_recalc(node, row_ids, should_prevent)`; `_maybe_update_trigger_dependencies()`; RecalcWhen constants DEFAULT=0 / NEVER=1 / MANUAL_UPDATES=2.
**Data Shape:** `_prevent_recompute_map: dict[Node, set[row_id]]` exempts rows from `_recompute_step` dirty evaluation; trigger-column metadata lives in _grist_Tables_column records (recalcWhen, recalcDeps, recalcOnChangesToSelf derived via MetaTableExtras.recalcOnChangesToSelf).

### Decisive source
```python
# docactions.BulkUpdateRecord — BEFORE invalidating the changed rows:
    if not col.is_formula():
      self._engine.prevent_recalc(col.node, row_ids, should_prevent=True)
      # Non-formula columns may get invalidated and recalculated if they have a trigger
      # formula. Prevent such recalculation if we set an explicit value for them (we want
      # to prevent it even if triggered by something else within the same useraction).

# useractions.doBulkUpdateRecord — AFTER applying the update:
    for col_id, col_obj in table.all_columns.items():
      if col_obj.is_formula() or not col_obj.has_formula():
        continue
      # Schedule for recalculation those trigger-formulas that depend on any manual update.
      if col_rec.recalcWhen == RecalcWhen.MANUAL_UPDATES:
        self._engine.invalidate_column(col_obj, row_ids, recompute_data_col=True)
      # For a data-cleaning column (one that depends on itself), a manual change *should*
      # trigger recalculation, so we un-prevent it here.
      if col_id in column_values and col_rec.recalcOnChangesToSelf:
        self._engine.prevent_recalc(col_obj.node, row_ids, should_prevent=False)

# schema.RecalcWhen (:391-394):
  DEFAULT = 0         # Calculate on new records or when any field in recalcDeps changes.
                      # If recalcDeps includes this column itself: a "data-cleaning" formula.
  NEVER = 1           # Do not calculate automatically (user can trigger manually).
  MANUAL_UPDATES = 2  # Calculate on new records and on manual updates to any data field.
```
Dependency edges for DEFAULT-mode columns are rebuilt wholesale by `Engine._maybe_update_trigger_dependencies`: when any trigger column metadata changed (docactions hook on _grist_Tables_column recalcWhen/recalcDeps edits), it clears and re-adds `Edge(out_node, in_node, SingleRowsIdentityRelation)` for every non-metadata table column with explicit recalcDeps.

**Flow:** explicit user value lands -> BulkUpdateRecord marks those rows prevented FIRST -> row invalidation would otherwise schedule the own-column trigger, but prevention suppresses it during this action AND any other trigger in the same useraction -> after apply, MANUAL_UPDATES columns get their rows invalidated for real; self-dependent (data-cleaning) columns get prevention LIFTED so manual edits do re-run cleaning -> whenever trigger metadata itself changes, all trigger dependency edges rebuild from scratch (conservative whole-doc sweep).
**Invariant:** an explicitly set value is never silently overwritten by its own column trigger unless the column declares itself data-cleaning; NEVER columns never auto-recalc; dependency-graph staleness after metadata edits is handled by full rebuild, not incremental patching.
**Probe:** `sandbox/grist/test_trigger_formulas.py::test_no_recalc_on_noop_change` (:77–84) and `test_recalc_with_direct_update` (:109–132); undo interplay pinned by `test_recalc_undo` (:155–189).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "grist-core", query: "recalcWhen MANUAL_UPDATES prevent_recalc trigger", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the prevent-window pattern (suppress own-trigger around explicit writes, lift for declared self-cleaning columns) and the rebuild-on-metadata-change stance. Adapt the three RecalcWhen modes and the recalcDeps metadata plumbing to your schema store; omit Grist raw-data-widget protections in doBulkUpdateRecord (view-section guards :522–564 are product-surface). Live-test caveat: python-plane runner blocked this lane; probes pinned to test lines.
