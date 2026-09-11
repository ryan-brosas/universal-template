<!-- capsule-v2 -->
# Structured-content vs error precedence — when a server flags isError, which payload carries the actionable text?

**Source:** OpenAI Agents Python MIT `main@fe45b415`; Codebase Memory project `openai-agents-python`. **Question:** MCP permits `structuredContent` alongside `isError: true` — should the tool output be the structured JSON or the content blocks?

## Error-content precedence policy
**Path/Symbol:** `src/agents/mcp/util.py`: decision at :770–780 inside the tool-invocation path; error-result flag read via `result_is_error(result)` (:776); per-block fallback serialization (:782–800); `is_error=result_is_error(result)` also recorded on ToolContext metadata (:631).
**Signature:** decision shape: `if server.use_structured_content and structured_content and not result_is_error(result): tool_output = json.dumps(structured_content) else: <content-block list>`.
**Data Shape:** single block → scalar dict; multiple blocks → list; unknown block types fall back to a TEXT block holding `model_dump_json()` (NOT `str()`, whose Python repr — single quotes, `None`/`True` — the model can't parse as JSON, :791–794).

### Decisive source
```python
# If structured content is requested and available, use it exclusively. Results the
# server flagged as errors keep their content instead, because that is where the
# actionable failure text lives. MCP permits ``structuredContent`` alongside
# ``isError``, so this is an error-content precedence policy in this SDK rather
# than the structured payload being invalid for a failed call. (:770-775)
```

**Flow:** success + structured requested/available → structured JSON wins exclusively → otherwise (error flagged, no structured content, or feature off) iterate `result.content`: text→text, image→data-URL image, other→JSON-in-text → wrap single vs list.
**Invariant:** Error results must surface their human-written failure text even when a structured payload exists — the structured body of a failed call is usually stale/empty and would hide the actual reason. A porter who drops the `not result_is_error(...)` conjunct silently converts every failed MCP call into opaque JSON.
**Probe:** `grep -n "not result_is_error(result)" src/agents/mcp/util.py` → 1 hit at :776 (the precedence gate). Direct tests: `tests/mcp/test_mcp_util.py::test_structured_content_skipped_for_error_results` (:2634), `::test_structured_content_used_for_non_error_results` (:2654, "An explicit isError=False result still prefers structured content").

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openai-agents-python", query: "structured_content result_is_error tool_output mcp invoke", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt error-beats-structured precedence for any tool bridge with dual payloads; adapt block-type handling to your schema; omit the data-URL image encoding if unsupported. Note: the queued "failed-conversion keeps-original" seam was checked against source at fe45b415 — util.py's conversion paths raise/log rather than keep-original; recorded as target-closed-with-finding rather than mined.
