<!-- capsule-v2 -->
# Generated-usercode rebuild — how does document schema become live table classes, and in what order does the Engine attach them?

**Source:** grist-core Apache-2.0 `main@c057666bb93b6f93a69b0884ce023676c3a2804b`; Codebase Memory `grist-core`. **Question:** How is the executable Python module for a document produced from schema alone, and how is it swapped into a running Engine without losing per-table state?

## Schema → module text → exec'd module
**Path/Symbol:** `sandbox/grist/gencode.py:GenCode.make_module` (:162-191), `GenCode._make_table_model` (:125-160), `exec_module_text` (:210-216); attach at `sandbox/grist/engine.py:Engine.rebuild_usercode` (:1127-1172).
**Signature:** `make_module(self, schema)`; `rebuild_usercode(self)`.
**Data Shape:** `schema` maps table_id → TableInfo with `columns` {colId → ColumnInfo(colId, type, isFormula, formula, ...)}. Output: full/user module texts plus `(table_id → UserTable)` dict; formula bodies cached across rebuilds two-generation (`_formula_cache` → `_new_formula_cache`) keyed `(table_id, col_id, formula)`.

### Decisive source
```python
# gencode.py :186-191
    # Once all formulas are generated, replace the formula cache with the newly-populated version.
    self._formula_cache = self._new_formula_cache
    self._new_formula_cache = {}
    self._full_builder = textbuilder.Combiner(fullparts)
    self._user_builder = textbuilder.Combiner(userparts)
    self._usercode = exec_module_text(self._full_builder.get_text())
```
```python
# engine.py :1148-1157
      # Process non-summary tables first so that summary tables
      # can read correct metadata about their source tables
      key = (hasattr(user_table.Model, '_summarySourceTable'), table_id)
      sorted_tables.append((key, table, user_table))
    sorted_tables.sort()

    # Now update the table model for each table, and tie it to its UserTable object.
    for _, table, user_table in sorted_tables:
      self._update_table_model(table, user_table)
      user_table._set_table_impl(table)
```

**Flow:** make_module groups summary tables by source via `summary.decode_summary_table_name` → emits header imports (`import grist`, `from functions import *`, `datetime, math, re`) once per builder → per table (sorted by id) a `@grist.UserTable class T:` block with DATA columns before FORMULA columns (`sorted(..., key=lambda c: c.isFormula)`), optional `_summarySourceTable = %r`, and a nested display-only `class _Summary:` whose formulas associate to the FAKE table id `"<T>._Summary"` (assoc_value None in codebuilder) → two-generation cache swap → only the FULL text is compiled as module filename `"usercode"` (registered into linecache so tracebacks show generated source) and exec'd. `rebuild_usercode` no-ops unless `self._should_rebuild_usercode`; reuses old `Table` objects by id, sorts NON-summary tables first by the tuple above, updates each model then `user_table._set_table_impl(table)`, routes removed tables through the same `_update_table_model(table, None)`, finishes with `docmodel.update_tables()`, `trigger_columns_changed()`, and clearing `_autocomplete_context`.
**Invariant:** Summary tables must be updated after their source table within the same rebuild pass; removed tables must be cleaned through the same update path (never dropped silently); the user-facing text is display-only and never executed.
**Probe:** `sandbox/grist/test_gencode.py:test_make_module_text` (:57-79) compares generated user text byte-for-byte against the sample embedded in `usercode.py.__doc__` — including an embedded `raise SyntaxError('invalid syntax', ('usercode', 1, 9, ...))` emitted for a malformed formula column; `test_summary.py:test_summary_gencode` (:217-247) pins exact `fetch_table_schema()` output including the `_Summary` group/count formulas.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "grist-core", mode: "ids", query: "gencode make_module rebuild_usercode", limit: 10 });
```

## Verdict
Adopt the two-text split (executable vs display), the fake-summary association trick, the non-summary-first attach ordering, and the two-generation formula-body cache. Adapt the linecache/filename trick to your host's source-mapping story. Omit `_grist_` metadata filtering if you have no hidden metadata tables.
