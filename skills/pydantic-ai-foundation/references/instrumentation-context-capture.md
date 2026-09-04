<!-- capsule-v2 -->
# Cross-task OTel context capture: attach-restore instead of detach-token

## Source / Question
`pydantic_ai_slim/pydantic_ai/_instrumentation.py::capture_current_context` (+ baggage plumbing) — How do you carry the OpenTelemetry context (and agent identity baggage) from the task that OWNS a span into a DIFFERENT task that iterates a stream, without cross-context detach blowing up? A porter will snapshot-and-detach and hit `ValueError: ... created in a different Context` on generator finalization.

## Path / Symbol
`pydantic_ai_slim/pydantic_ai/_instrumentation.py` — `capture_current_context` (547–577), `get_agent_run_baggage_attributes` (123–135), baggage keys `AGENT_NAME_BAGGAGE_KEY/RUN_ID_BAGGAGE_KEY/CONVERSATION_ID_BAGGAGE_KEY` (35–37); producer side `capabilities/instrumentation.py::wrap_run` (187–190 set_baggage + attach, 207 detach); consumer side `streamed-continuation-composite` capsule (`_ContinuationStreamedResponse._get_event_iterator`). Also `current_otel_traceparent` (643–654).

## Signature
```python
def capture_current_context() -> Callable[[], AbstractContextManager[None]]
# usage: cm = capture_current_context(); with cm(): ...   # in the CONSUMER task

def get_agent_run_baggage_attributes() -> dict[str, Any]  # reads the 3 gen_ai.* keys
```

## Data Shape
Captured value = `otel_context.get_current()` snapshot (an immutable OTel context). The factory returns a CM usable repeatedly, once per stream segment. Baggage keys: `gen_ai.agent.name`, `gen_ai.agent.call.id`, `gen_ai.conversation.id`.

## Decisive source
The restore path uses **re-`attach`, not `detach(token)`**:
```python
previous = otel_context.get_current()
otel_context.attach(captured)
try:
    yield
finally:
    otel_context.attach(previous)
```
The comment pins WHY (:563–569): the CM is held across `yield` inside the async-generator iterator, so when a streamed run is interrupted mid-segment the generator is finalized (`GeneratorExit`) in a *different* contextvars `Context`, where `otel_context.detach(token)` (= `ContextVar.reset`) raises `ValueError: … created in a different Context`; OTel swallows it but logs a noisy 'Failed to detach context' (surfaced verbatim in Pyodide output). `attach()` is a plain `set`, which never fails cross-context (#6569). Rationale for the whole seam (:551–557): the streaming continuation composite opens each segment's `request_stream` lazily in the CONSUMER task while the `chat` span was opened in another task; without re-attachment, `get_current_span()` updates (e.g. FallbackModel recording the resolved inner model onto the request span via span attributes) land on the wrong span.

## Flow / Invariant
Producer task: open span → build ctx = set_baggage(agent.name)→set_baggage(call.id, context=ctx)→set_baggage(conversation.id, context=ctx) → `token = attach(ctx)` → run → `finally: detach(token)` + set end-of-run attributes from the RESULT's messages (ctx.messages may be stale). Consumer task (per segment): `with capture_current_context()():` around the lazy iterator pull. Invariants: capture happens in the OWNER task at factory-call time, not at enter time; restore-by-attach is mandatory anywhere a captured CM can be finalized from another Context; downstream consumers read identity via `get_agent_run_baggage_attributes()` rather than parameters, so every span built outside the owner task still carries agent/run/conversation ids. `current_otel_traceparent()` is the no-span-created fallback: returns None for INVALID_SPAN else the W3C traceparent — used by OnlineEvaluation when the graph ran without its own span.

## Probe (direct test)
`tests/models/test_instrumented.py` — fallback-span attribution assertions exercise the captured-context path (see also `tests/models/test_fallback.py` time_to_first_chunk/fallback span pins); `test_logfire.py` pins baggage-derived attributes on child spans. Unit probe: call `capture_current_context()`, enter in one `contextvars.copy_context()`, finalize in another — no exception, restored context equals previous (mirrors #6569).

## Retrieve
`search_graph --project mnt-hdd-utopia-inspo-pydantic-ai --query 'capture_current_context otel_context attach GeneratorExit'`

## Verdict
**Adopt** attach-based restore for any context manager that can be finalized from a different contextvars Context — this generalizes beyond OTel (any ContextVar token). **Adopt** the baggage trio as the identity channel for nested spans. **Omit** `current_otel_traceparent` if your evaluation layer always owns its own span.
