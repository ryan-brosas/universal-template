<!-- capsule-v2 -->
# Declarative deferral & handle_call — how does requires_approval/kind='external' defer a tool without raising, and how does the single-call path stay in sync with the batch path?

**Source:** pydantic-ai MIT `main@b3cdbc96796f0294f1ac6943cdba70d14af8a0ef`; Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai` (full mode, coverage clean). **Question:** A tool can be deferred by declaration (`ToolDefinition.kind`) or by raising (`CallDeferred`/`ApprovalRequired`) — where must the declarative form be converted so both forms resolve identically, and what does the single-call convenience method return?

## ToolDefinition.defer + handle_call's gate
**Path/Symbol:** `pydantic_ai_slim/pydantic_ai/tools.py:ToolDefinition.defer` (740–746: `kind in ('external','unapproved')`, with `requires_approval: bool` at :306/:333 feeding kind `'unapproved'`); `tool_manager.py:ToolManager.handle_call` (1024–1124) + `_resolve_single_deferred` (1143–1242).
**Signature:** `handle_call(call, *, approved=False, metadata=None, wrap_validation_errors=True, on_inline_deferred=None, on_validate=None) -> ToolDenied | ToolReturn | Any`.
**Data Shape:** Return is polymorphic BY CONTRACT: raw value / `ToolReturn` wrapper = success; `ToolDenied` instance = denial (callers MUST isinstance-check — the message string alone is indistinguishable from a real return); typed errors for retry/fail.

### Decisive source
```python
# tool_manager.py:1094-1116 — convert DECLARATIVE deferral into a RAISED one
try:
    if (
        not approved
        and validated.args_valid
        and validated.deferral is None
        and (deferred_tool := validated.tool) is not None
        and deferred_tool.tool_def.defer          # <- kind-based, same source as the graph pipeline
    ):
        # Convert the *declarative* deferral into the raised one, right where every caller
        # passes, so the single resolution path below handles both forms identically...
        raise CallDeferred() if deferred_tool.tool_def.kind == 'external' else ApprovalRequired()
    return await self.execute_tool_call(validated, ...)
except (CallDeferred, ApprovalRequired) as exc:
    return await self._resolve_single_deferred(call, exc, ...)

# :1158-1160 — the sync demand, stated in-source
# NOTE: keep the dispatch branches here in sync with _agent_graph._call_tool —
# both paths must accept the full DeferredToolResult surface.
```

**Flow:** The graph pipeline classifies calls by kind BEFORE executing anything (`_collect_deferred_calls`), so declaratively-deferred tools never run there. `handle_call` executes first and reacts to what was raised — without the explicit `.defer` gate a `requires_approval=True` tool would simply run (approval silently skipped). After conversion, both raised-from-validator, raised-from-tool-body, and converted-declarative deferrals funnel into `_resolve_single_deferred`: capability handler consulted once → normalized result → approve-with-revalidation / deny-as-value / fail / retry / verbatim-return dispatch identical to `_tool_execution._call_tool`.
**Invariant:** Invalid arguments still take the execution path (raising as a retry) — matching the graph rule that only arg-valid calls may be collected/deferred. Handler-supplied retry signals always surface as `ToolRetryError` even under `wrap_validation_errors=False` (they're handler outputs, not validation failures). Denial is a VALUE, not an exception, in this API.
**Probe:** `tests/test_agent.py` approval suite (grep `ApprovalRequired`); `tests/test_exceptions.py` pins exception serialization (`kind: 'tool-failed'` wire shape etc.).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pydantic-ai", query: "handle_call ToolDefinition defer requires_approval _resolve_single_deferred", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the raise-at-the-shared-boundary pattern for declarative deferrals and the documented return-type contract; adapt which exceptions your host uses; omit realtime callbacks (`on_inline_deferred` observability) unless you have blocking consumers. Caveat: none — all ranges read at HEAD this session.
