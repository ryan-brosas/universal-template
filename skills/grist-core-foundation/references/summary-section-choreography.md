<!-- capsule-v2 -->
# Summary-section choreography — how does Grist re-point a view section onto a new summary table without ever showing inconsistent fields?

**Source:** grist-core Apache-2.0 `main@c057666bb93b6f93a69b0884ce023676c3a2804b`; Codebase Memory `grist-core`. **Question:** How are summary tables named/decoded from schema alone, and what ordering makes re-grouping an existing section atomic for clients?

## Name codec + section surgery order
**Path/Symbol:** `sandbox/grist/summary.py:encode_summary_table_name` (:80-87), `decode_summary_table_name` (:90-104), `summary_groupby_col_type` (:139-151), `SummaryActions.update_summary_section` (:226-310), `_create_summary_colinfo` (:333-353), `detach_summary_section` (:369-425).
**Signature:** `encode_summary_table_name(source_table_id, groupby_col_ids)`; `update_summary_section(self, view_section, source_table, source_groupby_columns)`.
**Data Shape:** summary table id = `<src>_summary` (+ `_<sorted groupby colIds>` when grouped); mandatory `group` formula column typed `RefList:<src>` with formula `table.getSummarySourceGroup(rec)`.

### Decisive source
```python
# summary.py :97-104 — decode WITHOUT metadata records
  group_col = summary_table_info.columns.get('group')
  if (
      group_col
      and 'getSummarySourceGroup' in group_col.formula
      and group_col.type.startswith('RefList:')
  ):
    return group_col.type[8:]   # source table id rides inside the type string
  return None
```
```python
# summary.py :264-271 — unset BEFORE field surgery
    # This line is a bit hard to explain: we unset viewSection.tableRef before updating all the
    # fields, and then set it to the correct value. ... Client-side code relies on this to
    # avoid having to deal with inconsistent view sections while fields are being updated.
    self.docmodel.update([view_section], tableRef=0)

    # Delete fields no longer relevant.
    self.docmodel.remove(delete_fields)
```

**Flow:** gencode decodes each summary table from schema alone by sniffing the `group` column (no metadata access needed). Group-by columns FLATTEN list types (`ChoiceList`→`Choice`, `RefList:X`→`Ref:X`, :139-151). Re-grouping keeps previous group columns plus formula columns; a dropped NUMERIC group-by returns as a sum "sister" column (`_append_sister_column_if_any` :321-330; sister = same-named formula col reused from any other summary of the same source). New sections get `group` + auto `count = len($group)` inserted right after it unless a custom count exists (:350-352). Surgery order is fixed: unset `tableRef=0` → remove dead fields → repoint surviving fields' colRefs → insert missing group fields after the last existing one → reorder group fields to requested order → remap `sortColRefs` via colRef translation (clearing it wholesale on any parse failure, `_update_sort_spec` :113-136) → finally set `tableRef` to the new summary table. `detach_summary_section` materializes a REAL table whose `group` formula becomes `<src>.lookupRecords($gcol=..., CONTAINS($listcol, match_empty=...))`, copies data via `ReplaceTableData`, and repeats the same unset/surgery/set dance.
**Invariant:** A view section must never be observed pointing at one table while carrying another table's field colRefs — hence unset-before-surgery and set-last; sortColRefs translation failure must clear, never corrupt.
**Probe:** `sandbox/grist/test_summary.py:test_summary_gencode` (:217-247) pins exact generated module text incl. nested `_Summary` formulas; `test_summary2.py:test_update_groupby_override` (:886-945) exercises the update path end-to-end.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "grist-core", mode: "ids", query: "update_summary_section detach_summary_section decode_summary_table_name", limit: 10 });
```

## Verdict
Adopt encode-into-name / decode-from-type-string naming, list-type flattening for group keys, sister-column reuse, and the unset-surgery-set ordering. Adapt sum-column defaults to your aggregation story. Omit widgetOptions copying details (rulesOptions stripping).
