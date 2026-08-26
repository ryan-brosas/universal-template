<!-- capsule-v2 -->
# Fetch-record live-rebuild tool — why must a dynamic tool re-read its data map on every execute instead of freezing it at registration?

**Source:** pipeshub-ai Apache-2.0 @ `main` (pin `6850972`); Codebase Memory `mnt-hdd-utopia-inspo-platforms-pipeshub-ai`. **Question:** when a tool's input domain grows mid-run (later searches add more fetchable records), how do you avoid serving a stale frozen snapshot — and what does "live" mean for the write-back map?

## Live virtual-records map + throwaway-default trap
**Path/Symbol:** `backend/python/app/agents/agent_loop/hooks/citations.py:147-272` (`_FetchFullRecordTool`, esp. `_live_virtual_records` :228-243 and `execute` :245-272); direct tests `backend/python/tests/unit/agents/agent_loop/hooks/test_citations.py` (5 tests).
**Signature:** `_FetchFullRecordTool(collector: CitationCollector, context: AgentContext)`, `.execute(**kwargs) -> ToolOutput`; accepted args exactly `("record_ids", "reason", "start_block", "max_blocks")`.
**Data Shape:** reads/writes `tool_state["virtual_record_id_to_result"]` dict; returns `ToolOutput(success, data)` where data is str OR multipart list of TextPart/ImagePart.

### Decisive source
```python
def _live_virtual_records(self) -> dict[str, Any]:
    """The mapping `_fetch_multiple_records_impl` writes downloaded records
    back into, so it must be the object in `tool_state` and NOT
    `CitationCollector.virtual_records`, whose `or {}` returns a throwaway
    dict while the map is empty — losing the write-back and re-downloading
    on every repeat fetch.
    Records persisting here skip the ACL re-check a fresh id gets; safe
    because `tool_state` is per HTTP request, hence per user."""
```

**Flow:** model calls with record_ids → unexpected-arg check returns a CORRECTABLE error for singular `record_id=` → `execute_fetch_record(virtual_records=self._live_virtual_records(), ...)` → if impl swapped the ref_mapper object, write the new one back into tool_state (`if ref_mapper is not ref_mapper_in` identity check).
**Invariant:** the tool rebuilds from the CURRENT map each call because retrieval REPLACES (`state[...] = {**existing, **new}`) rather than mutating — a registration-time snapshot would never see later searches. The live-map getter must return THE dict in tool_state (installing `{}` first if absent), never a defaulted copy, or write-backs vanish. Cached records deliberately skip fresh-id ACL re-checks; sound only because tool_state is per-request/per-user.

### Direct test
**Probe:** `tests/unit/agents/agent_loop/hooks/test_citations.py::test_multimodal_llm_image_record_returns_multipart_output` (:70) — image records deliver an ImagePart via multipart ToolOutput and stash NO fallback into `pending_tool_images` when native multipart support exists; exhausted-budget case degrades to text (:139). Execute: `/tmp/psh17venv/bin/python -m pytest tests/unit/agents/agent_loop/hooks/test_citations.py -q` (5 passed at pin).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-pipeshub-ai", query: "_live_virtual_records execute_fetch_record ToolOutput", limit: 5, fields: ["signature", "name", "file"] });
// resolves citations.py symbol cluster line-exact incl _FetchFullRecordTool members
```

## Verdict
Adopt live-rebuild semantics + the in-state-dict write-back rule for any mid-run-growing tool surface; adopt the correctable-error-on-singular-arg pattern. Adapt arg vocabulary and multipart delivery to your message-part types. Omit PipesHub record/blob specifics. Coverage caveat: none beyond best-effort graph signal.
