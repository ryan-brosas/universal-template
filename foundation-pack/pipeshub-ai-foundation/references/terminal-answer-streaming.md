<!-- capsule-v2 -->
# Terminal answer streaming — when does a model turn's text become THE answer, and how do preamble, citations, and confidence trailers stay off the wire?

**Source:** pipeshub-ai Apache-2.0 @ `main` (pin `6850972`); Codebase Memory `mnt-hdd-utopia-inspo-platforms-pipeshub-ai`. **Question:** a tool-calling turn can emit text first ("let me search...") — how do you stream the real answer live without faking it after completion or leaking preambles?

## Event-driven buffer with turn reset, tool-call clearing, and rate-limited citation refresh
**Path/Symbol:** `backend/python/app/agents/agent_loop/answer_streamer.py:81-232` (`TerminalAnswerStreamer`, consumed by `stream_bridge.py:323`); `_due_for_emit` :177-193, `_clear_preamble` :212-232, `on_event` :113-142.
**Signature:** `TerminalAnswerStreamer(context, collector, event_sink)`; `.on_event(event: AgentEvent)`; attribute `streamed_answer` read by AnswerFinalizer.
**Data Shape:** consumes TEXT_MESSAGE_START/CONTENT, TOOL_CALL_START, AGENT_COMPLETE, REASONING_MESSAGE_* events; emits formatter `answer_delta(chunk, accumulated, citations, confidence, raw_length)` SSE frames.

### Decisive source
```python
elif event.event_type == EventType.TOOL_CALL_START:
    # Skip clearing the buffer for terminal tools whose answer is
    # streamed via TEXT_MESSAGE_CONTENT deltas extracted from the
    # tool call arguments (e.g. final_answer.answer_markdown).
    tool_name = event.payload.get("tool", "")
    if not self._is_streaming_terminal_tool(tool_name):
        await self._clear_preamble()
elif event.event_type == EventType.AGENT_COMPLETE:
    self.streamed_answer = self._buffer
    if self._withheld and self._buffer:
        await self._emit_state_delta()
```

**Flow:** TEXT_MESSAGE_START resets buffer + snapshots citation state (stable mid-turn — no tools execute between first token and completion) → CONTENT deltas append; raw text streams per token while citation re-normalization is throttled to `PIPESHUB_ANSWER_DELTA_INTERVAL_MS` (default 250 ms) because it re-normalizes the WHOLE accumulated answer (was 22% of query-service CPU per-token) → TOOL_CALL_START clears the streamed preamble (that turn was never the answer) unless the tool is the streaming final-answer tool → AGENT_COMPLETE records `streamed_answer` and flushes ONLY what the limiter withheld.
**Invariant:** exactly one turn ends via AGENT_COMPLETE and its buffer IS the answer (Agent.step contract). The confidence trailer (`---\nConfidence: ...`) is parsed then stripped from every emitted frame INCLUDING partial states, but kept in raw `streamed_answer` for the finalizer. The withheld-flag flush avoids paying a duplicate full-size frame for turns the limiter never throttled.

### Direct test
**Probe:** `tests/unit/agents/adapter/test_answer_streamer.py` — 24 tests incl. `test_withheld_delta_is_flushed_at_agent_complete` :61, `test_no_extra_emit_when_nothing_was_withheld` :74, `test_tool_call_start_clears_streamed_preamble` :160, `test_trailer_never_reaches_the_wire` :288. Execute: `/tmp/psh17venv/bin/python -m pytest tests/unit/agents/adapter/test_answer_streamer.py -q` (24 passed at pin).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-pipeshub-ai", query: "TerminalAnswerStreamer on_event clear preamble withheld flush", limit: 4, fields: ["signature", "name", "file"] });
// resolves _clear_preamble Method answer_streamer.py 212-232 rank#1 + on_event 113-142 rank#2
```

## Verdict
Adopt the event-driven truth-source pattern: live per-token deltas on one channel, expensive enrichment (citations) rate-limited on another, preamble clearing keyed on TOOL_CALL_START with a terminal-tool carve-out, withheld-flush at completion. Adapt event names/formatter to your SSE dialect. Omit the legacy replay-streaming anti-pattern entirely.
