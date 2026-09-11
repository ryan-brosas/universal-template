<!-- capsule-v2 -->
# Typed reference columns & auto-reverse sync — how do Ref/RefList cells stay consistent with targets, including auto-managed reverse columns?

**Source:** grist-core Apache-2.0 `main@c057666bb93b6f93a69b0884ce023676c3a2804b`; Codebase Memory `grist-core`. **Question:** How are typed reference values converted without ever throwing, and how does a `reverse_of` column stay derived-from-forward at all times?

## Typed conversion + reverse-column registration
**Path/Symbol:** `sandbox/grist/usertypes.py:BaseColumnType.convert` (:156-175), `Reference(Id)` (:438-457), `ReferenceList` (:459-528), `DateTime.__init__` (:326-332), `reverse_source_node` (:455-457, :472-474); consumer `sandbox/grist/column.py:BaseReferenceColumn` (:417-441) and `prepare_new_values` (:498-514).
**Signature:** `convert(self, value_to_convert)`; `reverse_source_node(self) -> depend.Node | None`; `prepare_new_values(self, row_ids, values, ignore_data=False, action_summary=None) -> (values, adjustments)`.
**Data Shape:** column type string `Ref:<T>`/`RefList:<T>` (optionally `,reverse_of=<ColId>` per schema.py :400 note); stored cell = target row id(s); ReferenceList stores `objtypes.RecordList` row-id list or None (formulas see `[]`, docstring :504).

### Decisive source
```python
# usertypes.py :156-175 — convert NEVER throws
    if isinstance(value_to_convert, objtypes.RaisedException):
      return value_to_convert
    try:
      return self.do_convert(value_to_convert)
    except Exception as e:
      # If conversion failed, return a string to serve as alttext.
      try:
        return str(value_to_convert)
      except Exception:
        return objtypes.safe_repr(value_to_convert)
```
```python
# usertypes.py :455-457
  def reverse_source_node(self):
    """ Returns the reverse column as depend.Node, if it exists. """
    return depend.Node(self.table_id, self._reverse_col_id) if self._reverse_col_id else None
# column.py :500-505
    reverse_cols = self._target_table._reverse_cols_by_source_node.get(self.node, [])
    ...
      reverse_adjustments = reverse_references.get_reverse_adjustments(
          row_ids, old_values, values, self._value_iterable, self._relation)
```

**Flow:** every write goes through `convert`: RaisedException values pass through untouched; `do_convert` failures degrade to str() alttext then safe_repr. `Reference extends Id`: no float path, accepts int/Record only, enforces the same signed-32-bit bound (`is_int_short`, :419-431). `DateTime` falls back to `Zone('UTC')` when the timezone name is unknown (:329-332). `BaseReferenceColumn.__init__` resolves the target table and registers itself in `_target_table._back_references` AND, when the type carries `reverse_of`, in `_table._reverse_cols_by_source_node[depend.Node]` (:432-434); `destroy()` removes both (:437-444). On writes to the FORWARD column, `prepare_new_values` looks up reverse columns BY ITS OWN NODE on the TARGET table and emits adjustment actions computed from old vs new values via `reverse_references.get_reverse_adjustments`; `recalc_from_reverse_values` (:516-529) rebuilds a whole reverse column from the forward relation (sorted affected row ids). `ReferenceList.do_convert` also carries the table-RENAME hack: during renames Ref columns briefly become Int, so stringified JSON int-lists or `RecordList.from_repr(...)` strings must parse back (:476-497), list-of-RecordSets flatten+dedup preserving order (:509-514).
**Invariant:** Reverse columns are DERIVED state — always recomputable from forward values plus the relation; registration/removal must be symmetric with column lifecycle; invalid (alttext) reference values never contribute to reverse membership.
**Probe:** `sandbox/grist/test_twoway_refs.py:test_reverse_of_invalid_refs` (:1001-1031): after setting `Owner="invalid"` (alttext), AddReverseColumn still builds correct `Owners.Pets` lists and later valid updates keep them in sync while invalid cells persist harmlessly.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "grist-core", mode: "ids", query: "reverse_source_node BaseReferenceColumn prepare_new_values", limit: 10 });
```

## Verdict
Adopt total (never-throwing) typed conversion with alttext degradation, and reverse columns as derived state keyed by source node. Adapt the RecordList rename-survival hack only if you support renaming referenced tables in place. Omit `Attachments` (`ReferenceList('_grist_Attachments')`) specialization.
