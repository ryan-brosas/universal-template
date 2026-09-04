<!-- capsule-v2 -->
# debugger-only-draft-saver — Why do draft variables only persist in the editor?

**Source:** dify Apache-2.0 `main@8bdf702f`; Codebase Memory `ext-dify`. **Question:** How is per-node debug state captured without polluting production runs?

## Factory returns a real saver for DEBUGGER, Noop otherwise; adapter owns session scope
**Path/Symbol:** `api/core/app/apps/base_app_generator.py:BaseAppGenerator._get_draft_var_saver_factory` (:330-369); `_DebuggerDraftVariableSaver` (:34-68); port types in `api/core/app/apps/draft_variable_saver.py` (`NoopDraftVariableSaver` :31-34).
**Signature:** `_get_draft_var_saver_factory(invoke_from, account, *, tenant_id) -> DraftVariableSaverFactory`; saver `save(process_data, outputs)`.
**Data Shape:** Factory closure signature `(app_id, node_id, node_type, node_execution_id, enclosing_node_id=None) -> DraftVariableSaver`; debugger path opens `Session(db.engine)` + `session.begin()` PER SAVE.

### Decisive source
```python
if invoke_from == InvokeFrom.DEBUGGER:
    assert isinstance(account, Account)
    def draft_var_saver_factory(app_id, node_id, node_type, node_execution_id, enclosing_node_id=None):
        return _DebuggerDraftVariableSaver(account=account, tenant_id=tenant_id, app_id=app_id,
                                           node_id=node_id, node_type=node_type,
                                           node_execution_id=node_execution_id,
                                           enclosing_node_id=enclosing_node_id)
else:
    def draft_var_saver_factory(app_id, node_id, node_type, node_execution_id, enclosing_node_id=None):
        _ = app_id, node_id, node_type, node_execution_id, enclosing_node_id
        return NoopDraftVariableSaver()
```
```python
class _DebuggerDraftVariableSaver:
    """Adapter that binds SQLAlchemy session setup outside the saver port."""
    def save(self, process_data, outputs) -> None:
        with Session(db.engine) as session, session.begin():
            DraftVariableSaverImpl(session=session, ...).save(process_data, outputs)
```

**Flow:** generator picks the factory once per run by invoke source → pipeline calls it per saved event → debugger runs write process/outputs rows inside their own short transaction (saves are independent of the run's other writes); every other surface gets a Noop so call sites never branch on mode.
**Invariant:** The MODE CHECK lives at factory creation, not at save sites — consumers stay uniform; the adapter exists to keep transaction plumbing OUT of the port implementation; noop discard of all five args documents that the shape is contractual.
**Probe:** `grep -c '_join_worker_thread' core/app/apps/base_app_generator.py` → 2; direct test `tests/unit_tests/core/app/apps/test_base_app_generator.py::test_get_draft_var_saver_factory_debugger` (+ non-debugger twin asserting Noop).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-dify", query: "_DebuggerDraftVariableSaver draft variable saver factory noop", limit: 10 });
```

## Verdict
Adopt mode-selected factories with a Noop arm for debug-only side channels. Adapt what triggers "debug" and the storage behind the real saver. Omit nothing.
