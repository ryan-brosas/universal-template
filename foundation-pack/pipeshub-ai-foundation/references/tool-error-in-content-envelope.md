<!-- capsule-v2 -->
|# Tool error-in-content envelope — how do you surface failures from an LLM-facing tool whose return type cannot carry them?

**Source:** pipeshub-ai Apache-2.0 `main@68509725e15c`; Codebase Memory project `pipeshub-ai`. **Question:** A `@tool` returns a bare `str`, so the executor wraps it as always-successful — where do errors actually live, and who is allowed to read them?

## JSON-in-string envelope + content-parsing summaries
**Path/Symbol:** `backend/python/app/agents/actions/retrieval/retrieval.py` module comment block L86–95, error returns L300–310/L320–324/L456–486/L732–738; consumers `_search_internal_knowledge_result_summary` (L177–197).
**Signature:** `async def search_internal_knowledge(self, query: str | None = None, connector_ids: list[str] | None = None) -> "str | list[Part]"`.
**Data Shape:** success ⇒ human-readable `<record>` text (or multipart Parts); failure ⇒ single-line JSON `{"status": "error", "message": ..., "status_code"?}`. Empty-but-healthy ⇒ `{"status":"success","message":"No results found","results":[],"result_count":0}`.

### Decisive source
```python
# This tool returns a bare `str` rather than the `(bool, str)` tuple most
# connector tools use, so `ToolOutput.success` is ALWAYS True — errors are
# only visible as `{"status": "error", ...}` JSON in the content, which is
# why the result formatter parses that instead of trusting result.is_error.
...
def _search_internal_knowledge_result_summary(args, result):
    text = as_text(result.content)
    if not text: return None
    parsed = parse_json_maybe(text)
    if isinstance(parsed, dict) and parsed.get("status") == "error":
        return f"Search failed: {parsed.get('message') or 'Unknown error'}"
    if isinstance(parsed, dict) and (parsed.get("result_count") == 0 or ...):
        return str(parsed.get("message") or "No results found")
    match = _RETRIEVED_COUNT_RE.search(text)   # tolerant regex over LLM-facing text
```
(L86–95, L177–193.)

**Flow:** every failure path (missing query, missing state/services, upstream status ∈ {202,500,503}, None response, any exception) funnels into the SAME json.dumps error shape → the model sees a readable failure instead of an exception → activity summaries re-parse content because the wire flag lied.
**Invariant:** (1) Never branch on `ToolResult.is_error` for bare-str tools — parse the content envelope. (2) The envelope must be valid JSON on ONE line with a stable `status` key — summaries and tests depend on it. (3) Errors are data for the MODEL too: returning the message beats raising, which the loop would render as a generic tool failure. (4) Module-global `_SOURCE_LABELS` written per-request is concurrency-safe by UUID uniqueness (L49–52), so args summaries can resolve labels without locking.
**Probe:** EXECUTED at pin: `tests/unit/agents/actions/test_retrieval.py` :159–199 (query/state/service absence each assert parsed status+message), :297–307 (`RuntimeError("search engine down")` surfaces inside the JSON message); `test_retrieval_summaries.py::TestSearchInternalKnowledgeResultSummary.test_error_envelope` (:55–61) passes `is_error=True` AND an error body — summary keys off the BODY.
**Retrieve:** EXECUTED live — mcp__codebase-memory__search_graph project=`pipeshub-ai` file_pattern=`*agents/actions/retrieval*` query="result summary error envelope parse json status bare string tool output" → resolves `_search_internal_knowledge_result_summary` rank 1 plus args_summary/compose_result_tail.

## Verdict
Adopt the error-in-content envelope for any tool surface whose framework marks str-returning tools successful unconditionally; adopt content-parsing summaries alongside. Adapt the envelope fields to your schema (keep `status`). Omit only if your tool contract supports typed failure returns natively — then use them instead.

<!-- capsule-evidence: pipeshub-ai@68509725e15c retrieval.py L86–95/L177–197/L300–310/L732–738; test_retrieval.py, test_retrieval_summaries.py; live search_graph 2026-08-26 -->
