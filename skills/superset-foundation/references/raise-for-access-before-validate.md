<!-- capsule-v2 -->
# raise-for-access-before-validate — Why must the access decision come before query validation?

**Source:** Apache Superset Apache-2.0 `master@9f505eb0cbbc39b78f512765d82fd63cf5ad70e6`; Codebase Memory `superset`. **Question:** A chart-data request carries caller-supplied filter expressions that validation must render — in what order do authorization and validation run, and what goes wrong if the order flips?

## Authorization-before-validation ordering
**Path/Symbol:** `superset/common/query_context_processor.py` — `QueryContextProcessor.raise_for_access` (:756-772); `superset/commands/chart/data/get_data_command.py` — `ChartDataCommand.validate` (:100-101).
**Signature:** `raise_for_access(self) -> None`; `validate(self) -> None`.
**Data Shape:** routes on `self._qc_datasource.type`: `DatasourceType.QUERY` ⇒ `security_manager.raise_for_access(query=...)`, everything else ⇒ `security_manager.raise_for_access(query_context=...)`; then per-query `query.validate()`.

### Decisive source
```python
def raise_for_access(self) -> None:
    # Evaluate access before validating the queries: query validation
    # renders the request's filter expressions, so the access decision must
    # come first to avoid rendering caller-supplied input for a resource the
    # caller is not allowed to access.
    if self._qc_datasource.type == DatasourceType.QUERY:
        security_manager.raise_for_access(query=self._qc_datasource)
    else:
        security_manager.raise_for_access(query_context=self._query_context)

    for query in self._query_context.queries:
        query.validate()
```

**Flow:** every chart-data entry point (sync, async, cache-replay, nested viz-annotation execution) calls `ChartDataCommand.validate()` exactly once before any execution → that single call performs the datasource-type-routed authorization check FIRST → only on success does each query object validate (which renders Jinja filter expressions and normalizes extras).
**Invariant:** Authorization strictly precedes any rendering of caller-supplied input; a denied caller's filters are never rendered, templated, or normalized. The two datasource types must route to their distinct authorization entry points (saved-query objects vs full query contexts). This method is the single choke point — adding a second validate path that skips it breaks the ordering guarantee.
**Probe:** `tests/unit_tests/common/test_query_context_processor.py:2160-2191` pins the ordering directly: with `raise_for_access` patched to raise `SupersetSecurityException`, the test asserts `query.validate.assert_not_called()` — no query is validated when access is denied.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "superset", query: "raise_for_access evaluate access before validate render filter expressions", limit: 10 });
```

## Verdict
Adopt the documented ordering (authorize ⇒ then render/validate) as a hard invariant wherever validation has side effects on untrusted input; adapt the two-way datasource routing to your host's resource taxonomy; omit Superset's security-manager API shape. Coverage: processor read at :756-772; command file read whole (84L); direct test read at :2160-2191; MCP disconnected this pass — Retrieve is a documented target.
