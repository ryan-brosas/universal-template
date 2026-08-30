<!-- capsule-v2 -->
# Standalone-encoder run input — how does one event-stream class serve both a live HTTP request and a stream that arrived by some other transport?

**Source:** pydantic-ai Apache-2.0 `main@fde1bbb6aff461769a1d6d2440c33c232bf90f03`; Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** What must an event transformer do so it can encode events from runs it never started (durable workflow replay, queue fan-out, websocket relay) with no request object at all?

## run_input=None contract + transport surface
**Path/Symbol:** `pydantic_ai_slim/pydantic_ai/ui/_event_stream.py:` `run_input` field docstring (:103–111), `accept` field (:113–114), `message_id` (:116–117), `response_headers` (:163–166), `content_type` (:168–180), `encode_stream` (:187–190), `streaming_response` (:192–206); adapter-side twins `_adapter.py:` `transform_stream`/`encode_stream`/`streaming_response` (:440–471) each build a FRESH event stream.
**Signature:** `run_input: RunInputT | None = None`; `def streaming_response(self, stream: AsyncIterator[EventT]) -> StreamingResponse`.
**Data Shape:** subclass carries protocol values it needs as its OWN fields ("overwritten by the run input's value when one is given") — the base never reaches into `run_input` for behavior.

### Decisive source
```python
run_input: RunInputT | None = None
"""The protocol-specific run input object the stream was built from, if any.

`None` when the stream is used as a standalone encoder, transforming events that reached it
over a transport of their own — a durable execution workflow, a queue, a websocket fan-out —
rather than over the HTTP request a [`UIAdapter`][pydantic_ai.ui.UIAdapter] serves. A subclass
that needs a value the run input carries takes it as a field of its own, overwritten by the run
input's value when one is given.
"""
```

**Flow:** HTTP path: adapter.from_request parses body → build_event_stream(run_input) → run_stream_native → transform_stream → streaming_response. Non-HTTP path: construct the event-stream subclass directly (optionally `run_input=None`, e.g. tests pass `PartEndEventStream()` bare), feed ANY NativeEvent iterator into `transform_stream`, then either `streaming_response(...)` or drain `encode_stream(...)`.
**Invariant:** three rules:
1. All transform/closeout logic must be reachable without a request: no hook may require `run_input` — values derived from the request (message ids, accept header) live on the instance as plain fields with defaults (`message_id = uuid4()`, `accept=None`).
2. Starlette stays an OPTIONAL dependency: import inside `streaming_response` with an actionable `pip install "pydantic-ai-slim[ui]"` ImportError — the encoding plane works without it.
3. The content-type decision belongs to the subclass (`content_type` consults `accept`); the base only defaults to `text/event-stream` — a multi-format protocol (AG-UI accepts SSE vs JSON) overrides BOTH `encode_event` handling and `content_type` together.
**Probe:** `grep -c 'run_input=None' tests/test_ui.py` ≥ 1 and `grep -n 'PartEndEventStream()' tests/test_ui.py | head -2` (anchored at repo root; standalone-encoder construction without any adapter).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pydantic-ai", query: "UIEventStream transform_stream", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the standalone-encoder split (transport-neutral transform core; thin HTTP shell) whenever the same protocol events reach you via queue/websocket/durable-replay as via HTTP; adapt which fields your subclass hoists out of the run input; omit streaming_response if non-HTTP transports are your only target.
