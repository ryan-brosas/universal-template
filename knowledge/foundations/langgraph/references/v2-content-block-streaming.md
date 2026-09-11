<!-- capsule-v2 -->
# V2 content-block streaming — How does the v2 messages stream deliver content-block protocol events without breaking the v1 AIMessageChunk contract?

**Source:** LangGraph MIT `main@f09cfe8ffc1eeffd68f4b628ed69c30f7cad229f`; Codebase Memory `langgraph`. **Question:** A v3-protocol stream must show per-content-block deltas, but legacy `stream_mode="messages"` callers expect `(AIMessageChunk, metadata)` tuples — how are both served from one callback plane without double-emitting a message that was already streamed?

## A marker base class flips provider routing; run_id correlates events to streams
**Path/Symbol:** `libs/langgraph/langgraph/pregel/_messages.py:StreamMessagesHandlerV2` (:259-408); attach gate `libs/langgraph/langgraph/pregel/main.py` (:2773-2827, :3545-3558, :3601-3612); consumer routing `libs/langgraph/langgraph/stream/transformers.py:MessagesTransformer._route_protocol_event` (:292-322).
**Signature:** `class StreamMessagesHandlerV2(StreamMessagesHandler, _V2StreamingCallbackHandler)`; `on_stream_event(event: dict[str, Any], *, run_id: UUID, parent_run_id: UUID | None = None, tags: list[str] | None = None, **kwargs) -> Any`.
**Data Shape:** Emits `(ns, "messages", (event_dict, {**meta, "run_id": str(run_id)}))` where `event_dict["event"]` is one of `message-start`, `content-block-start`, `content-block-delta`, `content-block-finish`, `message-finish`, carrying `message_id`/`role`/`reason` fields. The handler is attached only when `version == "v2"` AND configurable carries `CONFIG_KEY_STREAM_MESSAGES_V2`; the v3 entrypoints (`_pregel_stream_v3`/`_apregel_stream_v3`) patch that key in before calling `stream`/`astream`.

### Decisive source
```python
    def on_llm_new_token(self, token, *, chunk=None, run_id, parent_run_id=None, tags=None, **kwargs):
        """Intentional no-op — v1 chunks are not used on v2-flagged runs. ..."""
        # Intentionally empty: v2 handler does not forward v1 chunks.

    def on_stream_event(self, event, *, run_id, parent_run_id=None, tags=None, **kwargs):
        if meta := self.metadata.get(run_id):
            if event.get("event") == "message-start":
                self._streamed_run_ids.add(run_id)
                msg_id = event.get("message_id")
                if msg_id:
                    self.seen.add(msg_id)
            v2_meta = {**meta[1], "run_id": str(run_id)}
            self.stream((meta[0], "messages", (event, v2_meta)))
```

**Flow:** Declaring `_V2StreamingCallbackHandler` as a base makes `BaseChatModel.invoke` route through `_stream_chat_model_events` (firing `on_stream_event`) instead of `_stream` (firing `on_llm_new_token`). Each protocol event is forwarded verbatim with `run_id` attached; the transformer keys open streams by `run_id` — `message-start` creates a `ChatModelStream` (tool-role starts go to `_ignored_runs`), `message-finish` closes it, and events with no prior start are dropped. On `message-start` the run joins `_streamed_run_ids` and its `message_id` joins `seen`, so when the node later returns the finalized AIMessage, `on_chain_end`'s dedupe skips it; `on_llm_end` emits the final message only for runs that were never streamed (non-streaming models emit exactly once), otherwise it just assigns/records the id. A v1 stream strips inherited V2 handlers from both `handlers` and `inheritable_handlers` (keeping v1 handlers, which outer streams rely on), so content-block events never leak into the v1 protocol. The v2 node-output scan additionally skips `ToolMessage` values — tool results belong on the tools channel in v3.
**Invariant:** Exactly one representation per message reaches the consumer — streamed protocol events OR the final AIMessage, never both; v1 chunks never appear on a v2-flagged stream; a v1 stream never observes a V2 handler.
**Probe:** `python -m pytest tests/test_stream_messages_transformer.py::TestProtocolEventRouting -q` — 9 passed (start creates stream, full lifecycle yields done stream, tool-role protocol events ignored, concurrent streams routed by run_id, events without prior start ignored, stream pushed on start not finish, legacy v1 chunks ignored). Byte-exact: `grep -c "Intentionally empty: v2 handler does not forward v1 chunks." libs/langgraph/langgraph/pregel/_messages.py` → 1; `grep -c "self._streamed_run_ids.add(run_id)" .../_messages.py` → 1; `grep -c "CONFIG_KEY_STREAM_MESSAGES_V2" .../pregel/main.py` → 5; `grep -c "self._by_run[run_id] = stream" .../stream/transformers.py` → 1.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "langgraph", query: "StreamMessagesHandlerV2 on_stream_event content-block message-start", limit: 8 });
```

## Verdict
Adopt the marker-base-class trick (a base declaration flips provider-side routing between token callbacks and protocol-event callbacks), the run_id correlation key between emitter and transformer, and the streamed-run registry + seen-set for exactly-once across streaming and final output. Adapt the event vocabulary to your host's provider protocol and keep the v1/v2 strip-on-v1-stream rule if you support both shapes. Omit the dual protocol entirely if your host has only one wire format — then the dedupe registry alone is the portable invariant.
