<!-- capsule-v2 -->
# Pair-safe truncation index — How do you cut a transcript mid-run without orphaning a tool call?

**Source:** agno Apache-2.0 `main@9644f22982ae017eaa4ad85c561d927d9ac03119`; Codebase Memory `ext-agno`. **Question:** Where may a time-travel boundary land so providers don't reject the truncated history with a 400?

## Snap DOWN to the nearest boundary that keeps every kept tool_call answered
**Path/Symbol:** `libs/agno/agno/utils/message.py:safe_truncation_index` (:10-47); consumers `_truncate_run_to_checkpoint` (`libs/agno/agno/agent/_run.py`:2966-3027) and `_fork_run` (:3029-3070).
**Signature:** `safe_truncation_index(messages: Sequence[Message], requested_index: int) -> int`.
**Data Shape:** pure function over Message records; reads `tool_call_id` (tool-role answers) and `tool_calls[].id` (assistant batch owners); returns an index ≤ requested.

### Decisive source
```python
# Map each tool_call_id to the index of the tool-role message that answers it.
result_at: Dict[str, int] = {}
for idx, message in enumerate(messages):
    tool_call_id = getattr(message, "tool_call_id", None)
    if tool_call_id:
        result_at[tool_call_id] = idx

for idx in range(requested_index):
    for tool_call in getattr(messages[idx], "tool_calls", None) or []:
        call_id = tool_call.get("id") if isinstance(tool_call, dict) else getattr(tool_call, "id", None)
        result_index = result_at.get(call_id)
        if result_index is None or result_index >= requested_index:
            # Drop this incomplete exchange (and everything after it).
            return idx
return requested_index
```

**Flow:** `_truncate_run_to_checkpoint` snaps via safe_truncation_index (logging when it moved), slices messages, then rebuilds validity: a kept tool needs its tool_call_id referenced by a surviving message; a requirement survives iff its `tool_execution.tool_call_id` survived; checkpoint marker updated. `_fork_run` snaps BEFORE deep-cloning so fork metadata (`forked_from_message_index`) matches the truncation actually performed.
**Invariant:** An assistant message carrying `tool_calls` whose results fall outside the prefix makes the transcript invalid for OpenAI/Anthropic — the boundary must snap DOWN to the offending assistant's own index, dropping the whole incomplete exchange rather than keeping half of it. Boundaries produced by regenerate/last_user/end never split batches, so the snap is a no-op for them by construction.
**Probe:** `grep -n 'safe_truncation_index(' libs/agno/agno/agent/_run.py` → exactly **2** sites (:2992 truncate path, :3051 fork path); direct behavior tests `libs/agno/tests/unit/agent/test_unified_continue.py::TestTruncatePairSafety::test_cut_between_assistant_and_result_snaps_down`, `::test_cut_inside_result_batch_snaps_down`, `::test_complete_exchange_boundary_is_not_snapped`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-agno", query: "safe_truncation_index", limit: 5, fields: ["signature", "name", "file"] });
```
(resolves line-exact 10-47.)

## Verdict
Adopt the pure function verbatim (it has no framework dependencies); adapt Message attribute access to your record type; omit the warning log pairing if you lack structured logging.
