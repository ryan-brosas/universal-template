<!-- capsule-v2 -->
# Global-catalog fallback — how should "tool exists but isn't attached" differ from "no such tool"?

**Source:** pipeshub-ai Apache-2.0 `main@4a02110dd9a7a644d8ba7a5ccd295c58a3c3628f`; Codebase Memory `pipeshub-ai`. **Question:** When `search_tools` has zero hits in THIS agent's registry, how do you surface org-wide tools the model may request the user to attach — without leaking an execute path?

## Zero-hit-only Protocol seam + not_attached default reason
**Path/Symbol:** `backend/python/app/agent_loop_lib/tools/global_fallback.py:GlobalToolHit/GlobalCatalogFallback` (L27–45); consumption in `tools/builtin/lazy_toolsets.py:SearchToolsTool.execute/_search_global_fallback` (L322–361).
**Signature:** `async def search(self, query: str, limit: int) -> list[GlobalToolHit]` — host-implemented (`@runtime_checkable` Protocol); `global_fallback=None` is a true no-op.
**Data Shape:** `GlobalToolHit{name, toolset?, description, reason="not_attached"}`; result payload carries `matches: []` + `unavailable: [...]` + a message telling the model what to tell the user.

### Decisive source
```python
# SearchToolsTool.execute:
matches = await self._index.search(self._registry, query, limit)
if not matches:                                   # ONLY on zero local hits
    unavailable = await self._search_global_fallback(query, limit)
    if not unavailable:
        return ... {"message": "No tools matched your query. Try list_toolsets..."}
    return ToolOutput(success=True, data={
        "matches": [],
        "unavailable": unavailable,
        "message": ("No attached tool matched your query, but a matching "
                    "tool exists — see `unavailable` for what to tell the user."),
    })

# GlobalToolHit docstring: reason defaults to "not_attached" — the ONLY
# reason a search-time fallback can determine on its own; "not_authenticated"
# is a distinct EXECUTE-time signal (tool_adapter.py ToolsetAuthError
# handling), never produced from a search miss.
```

**Flow:** local index miss → optional fallback query → hit ⇒ success payload with `unavailable` rows + SSE `EventType.TOOL_UNAVAILABLE` per hit (frontend renders attach/connect prompts) → no wiring ⇒ identical legacy behavior.
**Invariant:** (1) Fallback fires ONLY at zero local hits — it never dilutes real matches. (2) A fallback hit grants NOTHING executable; it produces user-facing guidance, keeping search/read-only and execute/authorized strictly separate. (3) Reason vocabulary is split by phase: search can only ever say "not_attached"; auth failures belong to execution. (4) DIP: the library defines the shape; PipesHub supplies the process-wide catalog implementation at wiring time.
**Probe:** `tests/unit/agent_loop_lib/tools/test_lazy_toolsets.py::test_handle_emits_tool_unavailable_sse_event_per_hit` (:248) + assertions at :222/:234/:246/:260 pinning when `unavailable` appears vs absent and per-hit SSE emission.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pipeshub-ai", query: "GlobalCatalogFallback GlobalToolHit _search_global_fallback TOOL_UNAVAILABLE", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the tri-state answer (match / exists-unattached / nothing) for any per-agent tool subset over a larger catalog; adapt reason strings/SSE event names to host. Omit PipesHub's `_global_tools_registry`. Direct tests pin payload shapes and SSE emission; the no-op default keeps unwired callers byte-identical.
