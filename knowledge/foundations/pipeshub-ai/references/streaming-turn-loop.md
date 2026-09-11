<!-- capsule-v2 -->
# Streaming turn loop — how do you emit per-token AG-UI deltas while still assembling exactly one authoritative ModelResponse?

**Source:** pipeshub-ai Apache-2.0 `main@4a02110d`; Codebase Memory `pipeshub-ai`. **Question:** How do you stream text/thinking/tool-arg deltas without letting the stream become the source of truth?

## Stream events are presentation; StreamCompleteEvent is truth
**Path/Symbol:** `backend/python/app/agent_loop_lib/agent/__init__.py` streaming branch of `_call_llm` (645-718); `Agent.stream()` delegating to `agent/streaming.py` (:1003-1008); event types in `core/streaming.py` (`TextDeltaEvent`, `ThinkingDeltaEvent`, `ToolCallDeltaEvent`, `StreamCompleteEvent`).
**Signature:** `async for event in self._model.stream(messages, tools, system, model, ...) -> None` terminated by exactly one `StreamCompleteEvent(response: ModelResponse)`.
**Data Shape:** `_fa_extractors: dict[int, StreamingJsonStringExtractor | None]` keyed by tool-call index — only final_answer calls get a live extractor; other tools' arg deltas are deliberately dropped.

### Decisive source
```python
# agent/__init__.py:682-706 — final_answer args are re-routed into the
# text-delta channel so terminal answers stream like plain text.
elif isinstance(event, ToolCallDeltaEvent):
    """Route argument deltas for final_answer into TEXT_MESSAGE_CONTENT
    so TerminalAnswerStreamer and AG-UI receive them unchanged. For all
    other tools the delta is intentionally dropped here — the fully
    assembled call from StreamCompleteEvent is what matters."""
    idx = event.index
    if idx not in _fa_extractors:
        if final_answer_enabled() and event.name == FinalAnswerTool().name:
            _fa_extractors[idx] = StreamingJsonStringExtractor("answer_markdown")
        else:
            _fa_extractors[idx] = None  # not a final_answer call
# :716-717 — the missing-terminal guard
if final_response is None:
    raise AgentError("Model.stream() completed without a StreamCompleteEvent")
```

**Flow:** TEXT_MESSAGE_START once per streamed turn → thinking deltas open/close their own REASONING_MESSAGE envelope (lazily opened on first thinking delta; closed when text starts — reasoning always precedes text) → text deltas flow as CONTENT → tool-arg deltas feed only the final_answer extractor (one "still working" state write on first non-final delta so long silent calls don't look dead) → StreamCompleteEvent carries the full ModelResponse that step() actually records → REASONING/TEXT_MESSAGE_END; missing terminal event ⇒ AgentError. `Agent.stream(goal)` wraps run() yielding these AgentEvents and stashes the final result on `last_stream_result`.
**Invariant:** Deltas never mutate conversation history; the assembled response from StreamCompleteEvent is the ONLY thing added to context. Exactly one TEXT_MESSAGE_END per stream even for tool-only turns; child agents mirror into the parent's emitter via run_child(mirror_events=True) flipping `.streaming` before run().
**Probe:** `tests/unit/agent_loop_lib/agent/test_streaming.py::test_normal_completion_sets_last_stream_result` (:51), `::test_cancelling_the_consumer_cancels_the_underlying_run` (:61); `tests/unit/agent_loop_lib/runtime/test_run_child_streaming.py::test_child_agent_is_flipped_to_streaming_before_run` (:42), `::test_mirror_events_false_opts_child_out_of_streaming` (:85).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pipeshub-ai", query: "TextDeltaEvent ThinkingDeltaEvent ToolCallDeltaEvent StreamCompleteEvent StreamingJsonStringExtractor", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt deltas-as-presentation with a single terminal completion event, lazy reasoning envelopes, and selective arg re-routing for the answer tool; adapt event names to your UI protocol; omit the StreamingJsonStringExtractor unless you stream a JSON-string field incrementally. Direct tests pin completion-result wiring, consumer-cancel propagation, and child mirroring opt-out; caveat: no dedicated test pins the final_answer re-route itself.
