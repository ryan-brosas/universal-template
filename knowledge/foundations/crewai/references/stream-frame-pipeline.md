<!-- capsule-v2 -->
# Stream frame pipeline — contextvar sinks, channel taxonomy, and thread-bridge generators

**Source:** crewAI MIT `main@9e9a8577`; Codebase Memory `ext-crewAI`. **Question:** How do internal events become ordered public stream frames (sync AND async) without coupling the event bus to consumers?

## Connected graph-selected seam
**Path/Symbol:** `lib/crewai/src/crewai/utilities/streaming.py` — `_stream_channel` (:143), `create_frame_streaming_state` (:208), `create_frame_generator` (:254), `register_cleanup` (:400); sink registry in `events/stream_context.py`.
**Signature:** `create_frame_generator(state, run_func, output_holder) -> Iterator[StreamFrame]`; `_stream_channel(event: BaseEvent) -> StreamChannel` (one of llm/messages/flow/tools/lifecycle/custom).
**Data Shape:** `FrameStreamingState` = sync_queue + optional async_queue + sink callable + result_holder; frames carry typed chunks (content/tool_call/event) with channel+namespace tags.

### Decisive source
```python
# :143 the public channel taxonomy is pure event-type dispatch
def _stream_channel(event: BaseEvent) -> StreamChannel:
    if isinstance(event, LLMEventBase):          return "llm"
    if isinstance(event, ConversationMessageAddedEvent): return "messages"
    if isinstance(event, FlowEvent):             return "flow"
    if isinstance(event, ToolUsageEvent | ToolExecutionErrorEvent): return "tools"
    if "error" in event.type or "failed" in event.type:  return "lifecycle"
    return "custom"

# :261 sync generator runs the WHOLE flow on a daemon thread w/ copied context
def run_with_sink() -> None:
    token = add_stream_sink(state.sink)     # contextvar-scoped sink
    try:
        result = run_func()
        state.result_holder.append(result)
    except Exception as e:
        _signal_frame_error(state, e)       # error becomes a queued ITEM
    finally:
        reset_stream_sinks(token)
        _signal_frame_end(state)            # None sentinel ends the queue

ctx = contextvars.copy_context()
thread = threading.Thread(target=ctx.run, args=(run_with_sink,), daemon=True)
```

**Flow:** kickoff(stream=True) → build state + register contextvar sink → run flow on daemon thread (sync) or task (async) → every bus event passes through publish_stream_event → sink converts event→frame via channel/namespace tagging → generator yields frames; exceptions arrive as raised items, end as None sentinel → finally joins thread and finalizes session result. Sinks live in a ContextVar tuple so nested/concurrent streams don't cross-deliver.
**Invariant:** The run ALWAYS executes on another thread with `contextvars.copy_context()` — otherwise the producer's contextvars (sinks!) wouldn't be visible to events emitted inside pool threads. Errors are DATA on the queue (raise-on-dequeue), never printed. The None sentinel is the only legal EOF.
**Probe:** `grep -c 'threading.Thread(target=ctx.run' lib/crewai/src/crewai/utilities/streaming.py` → `2`; direct suites: `/tmp/crewai-p1-venv/bin/python -m pytest tests/test_streaming.py tests/test_stream_frames.py -q -p no:xdist -o addopts=''` → green (52 passed combined with thread-safety suite).
**Direct test:** `tests/test_streaming.py::TestFlowKickoffStreaming::test_streaming_kickoff_passes_checkpoint_config_to_stream_events` (:513); `tests/test_stream_frames.py` frame-contract table.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-crewAI", query: "create_frame_generator scoped synchronous public frame generator", limit: 5 });
// → ext-crewAI...utilities.streaming.create_frame_generator Function 254-289
```

## Verdict
Adopt contextvar-sink + sentinel-queue + thread-bridge streaming for any event-bus-to-consumer API. Adapt channel names to host taxonomies. Omit CrewAI's TUI-specific frame fields.
