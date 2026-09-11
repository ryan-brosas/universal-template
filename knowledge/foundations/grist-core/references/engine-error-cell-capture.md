<!-- capsule-v2 -->
# Error-into-cell capture — when a formula raises, what exactly lands in the cell, and how do read paths expose it?

**Source:** grist-core Apache-2.0 `main@c057666bb93b6f93a69b0884ce023676c3a2804b`; Codebase Memory `grist-core`. **Question:** How does one cell evaluation capture arbitrary user exceptions (and pending reordering requests) into typed cell payloads without ever propagating them out of the engine?

## Bare-except capture with checkpoint rollback (engine.py + objtypes.py)
**Path/Symbol:** `sandbox/grist/engine.py:Engine._recompute_one_cell` (:946–1017), `get_formula_value` (:728–741), `get_formula_error` (:708–726); `sandbox/grist/objtypes.py:RaisedException` (:261–352, wire tag "E").
**Signature:** `_recompute_one_cell(table, col, row_id, cycle=False, node=None, record_attributes=None) -> value|RaisedException`; `get_formula_value(table_id, col_id, row_id, record_attributes=None)`.
**Data Shape:** success returns the raw Python value; failure returns RaisedException(error, include_details, user_input) where error is the caught exception object, details holds a traceback only when included, user_input preserves the prior cell value of trigger formulas; encodes as ["E", name, message, details?, {u: input}?] with trailing Nones trimmed.

### Decisive source
```python
value = None
with self._timing.measure(col.node):
  try:
    if cycle:
      raise depend.CircularRefError("Circular Reference")
    if not col.is_formula():
      value = col.get_cell_value(int(record), restore=True)
      with FakeStdStreams():
        result = col.method(record, table.user_table, value, self._user)
    else:
      with FakeStdStreams():
        result = col.method(record, table.user_table)
    if self._cell_required_error:
      raise self._cell_required_error   # formula consumed/swallowed it; reorder must still happen
    return result
  except MemoryError:
    raise                              # do not wrap memory errors
  except:                              # bare except: untrusted code may raise anything
    order_error = self._cell_required_error
    regular_error = sys.exc_info()[1] if not order_error else None
    self._undo_to_checkpoint(checkpoint)   # roll back side-effect doc actions (lookupOrAddDerived...)
    if order_error:
      self._cell_required_error = None
      raise order_error                # cell evaluation gets reordered in response
    include_details = (node not in self._is_node_exception_reported) if node else True
    if not col.is_formula():
      return objtypes.RaisedException(regular_error, include_details, user_input=value)
    else:
      return objtypes.RaisedException(regular_error, include_details)
```
The read-side twins: `get_formula_value` wraps one-cell evaluation in checkpoint/undo-to-checkpoint and forces `_sync_request` so REQUEST calls block instead of deferring; `get_formula_error` recomputes that single cell, and if the error has already healed for a TRIGGER formula it decodes the stored cell error and returns `no_traceback()`.

**Flow:** checkpoint -> FakeStdStreams around untrusted call -> success still honors a swallowed pending cell-required error (raise it so the update loop reorders) -> MemoryError passes through unwrapped -> bare except prefers a pending OrderError over the regular exception, rolls side-effect actions back to the checkpoint BEFORE raising, otherwise returns RaisedException AS the cell VALUE -> `_recompute_step` logs full details once per node (_is_node_exception_reported) then strips details from subsequently stored exceptions -> validation columns coerce to boolean.
**Invariant:** user exceptions never propagate out of cell evaluation; they become typed cell payloads that ride normal change recording (strict_equal compare, calc/stored actions) — but traceback DETAILS survive only for the first failing cell per node per round, and any doc-actions a failed formula produced are undone before reordering raises.
**Probe:** `sandbox/grist/test_engine.py::EngineTestCase.assertFormulaError` (:277–291 asserts objtypes.RaisedException instance, error type, _message, regex-checked details traceback) used across `test_formula_error.py`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "grist-core", query: "RaisedException _recompute_one_cell formula error capture", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt errors-as-values with per-node detail stripping, the swallow-proof pending-error re-raise, and checkpoint rollback of formula side effects. Adapt the payload type/wire encoding to your marshalling layer; omit the trigger-formula user_input channel and validation-column coercion unless your cells carry prior-value semantics too. Live-test caveat: python-plane runner blocked this lane; probe pinned to helper source lines.
