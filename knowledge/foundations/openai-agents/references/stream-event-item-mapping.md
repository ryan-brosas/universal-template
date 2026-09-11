<!-- capsule-v2 -->
# Stream-event item mapping — which RunItem types become public stream events and which are deliberately silent?

**Source:** OpenAI Agents Python MIT `main@cb8a2e7e`; Codebase Memory project `openai-agents-python`. **Question:** What is the complete RunItem→RunItemStreamEvent name mapping, and which items must never surface?

## Closed isinstance ladder + silent classes
**Path/Symbol:** `src/agents/run_internal/streaming.py:` `stream_step_items_to_queue` (:28–65), `stream_step_result_to_queue` (:68–73).
**Signature:** `def stream_step_items_to_queue(new_step_items: list[RunItem], queue: asyncio.Queue[StreamEvent | QueueCompleteSentinel]) -> None`.
**Data Shape:** emitted names: message_output_created / handoff_requested / handoff_occured / tool_called / tool_search_called / tool_search_output_created / tool_output / reasoning_item_created / mcp_approval_requested / mcp_approval_response / mcp_list_tools.

### Decisive source
```python
elif isinstance(item, ToolApprovalItem):
    event = None  # approvals represent interruptions, not streamed items
elif isinstance(item, CompactionItem):
    event = None  # compaction items are session bookkeeping, not streamed items
else:
    logger.warning("Unexpected item type: %s", type(item))
    event = None
```

**Flow:** single pass over step items → isinstance ladder assigns each item exactly one event name (or silence) → `put_nowait` onto the bounded stream queue. Approval items and compaction records exist in history but never as consumer events; unknown future types log-and-skip rather than crash the stream.

**Invariant:** The mapping is CLOSED: adding a new RunItem type requires extending this function or it silently disappears from streams (by design — fail-quiet with warning). Consumers rely on exact event-name strings; note the upstream misspelling `handoff_occured` is API surface.

**Probe:** `tests/test_stream_events.py:479` pins `message_output_created` within a full ordering assertion.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openai-agents-python", query: "stream step items to queue run item stream event names", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the closed-mapping-with-default-silent pattern for any internal record type crossing a public event bus; adapt names freely (but keep them stable once released).
