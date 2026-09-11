<!-- capsule-v2 -->
# Cognify route resolver — which task list does one data item run?

**Source:** cognee (Apache-2.0) `main@a8f9760b`; Codebase Memory `ext-cognee`. **Question:** When a cognify run mixes documents, DLT manifests, and code files, how is each item assigned its task list without letting an unmapped route silently fall through to the LLM pipeline?

## Pure routing policy (module docstring contract)
**Path/Symbol:** `cognee/modules/cognify/routing.py:cognify_route_for` (:39-41), `CognifyRoute` (:23-29).
**Signature:** `def cognify_route_for(data_item) -> CognifyRoute`.
**Data Shape:** Reads only the routing fact written onto each Data record at add time (`system_metadata`/`extension`); user-writable `external_metadata` is NEVER consulted. `_ROUTE_BY_DOCUMENT_CLASS = {DltSourceDocument: DLT_SOURCE, CodeFileDocument: CODE, CodeRepoDocument: CODE_REPO}`; anything else → `STANDARD`.

### Decisive source
```python
def document_class_for(data_item): ...   # from tasks.documents.classify_documents

def cognify_route_for(data_item) -> CognifyRoute:
    """The cognify route for one data item. Pure function of the record."""
    return _ROUTE_BY_DOCUMENT_CLASS.get(document_class_for(data_item), CognifyRoute.STANDARD)
```

**Flow:** `cognify()` builds ALL task lists up front (`tasks_by_route`, cognify.py :309-316 — STANDARD/DLT_SOURCE/CODE/CODE_REPO, each wired EXPLICITLY including standard) → wraps them in a sync closure `resolve_cognify_tasks(data_item)` (:318-319) → passes the closure to `run_pipeline(tasks=resolve_cognify_tasks)` so `run_tasks` resolves per item inside one shared dataset run.
**Invariant:** The closure must be SYNC (the distributed runner materializes per-item task columns and needs concrete lists, not an async factory). An enum member added without a task-list entry raises KeyError at resolution time BY DESIGN — never add a `.get(..., tasks)` fallback, or code routed away from the LLM list would silently run the LLM list.
**Probe:** `cognee/tests/unit/modules/cognify/test_cognify_single_logical_run.py::TestRouting` (`test_manifest_routes_to_dlt_source`, `test_unmapped_route_raises_instead_of_defaulting` — pins KeyError over silent default; `test_user_external_metadata_cannot_steer_routing`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-cognee", query: "cognify_route_for", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the pure-function router + explicit-route-table + fail-loud-KeyError trio; adapt the document-class set to your own item taxonomy; omit cognee's specific DLT/code document classes if your host has no such sources.
