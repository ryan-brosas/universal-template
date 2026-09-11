<!-- capsule-v2 -->
# Event vocabulary & status field — how do legacy consumers, AG-UI frontends, and reasoning deltas share one emitter without breaking each other?

**Source:** pipeshub-ai Apache-2.0 `main@c28d133…`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-pipeshub-ai`. **Question:** How do you extend an event enum across three dialect generations (legacy → AG-UI → reasoning) while keeping every existing consumer working — and how do consumers tell a blocked tool result from a completed one?

## Additive aliasing + one explicit status field replacing three copies of key-sniffing
**Path/Symbol:** `backend/python/app/agent_loop_lib/events/base.py:EventType/ToolCallStatus/AgentEvent/EventEmitter/CompositeEmitter` (:13 / :72 / :93 / :108 / :116).
**Signature:** `class EventType(str, Enum)`; `class ToolCallStatus(str, Enum): SUCCESS/ERROR/BLOCKED`; `async def emit(self, event: AgentEvent) -> None`.
**Data Shape:** `AgentEvent(event_id=uuid4, event_type, run_context, payload=dict)`. Legacy names (AGENT_START…HIL_RESPONDED), AG-UI-aligned additive block (RUN_STARTED/FINISHED/ERROR, TEXT_MESSAGE_*, TOOL_CALL_START/END, STATE_SNAPSHOT/DELTA), REASONING_MESSAGE_* suite named after AG-UI's CURRENT names — NOT the THINKING_* names AG-UI removed in 1.0. TOOL_UNAVAILABLE payload `{tool, toolset, reason, message}` with reason ∈ not_attached/not_authenticated.

### Decisive source
```python
class ToolCallStatus(str, Enum):
    """Explicit payload["status"] carried on every TOOL_RESULT/
    TOOL_BLOCKED event — the ONE field consumers should read to tell a
    blocked call apart from a completed (successful or failed) one.
    Both event types alias onto the SAME EventType.TOOL_CALL_END for
    AG-UI-shaped consumers … so before this field existed,
    SSEEventEmitter/AGUIEventEmitter/TranscriptCollector each had to
    independently re-derive "was this actually a TOOL_BLOCKED" by sniffing
    which payload KEYS happened to be present ("reason" in payload and
    "is_error" not in payload) — three copies of the same fragile
    inference, one per consumer, that broke silently if a producer's key
    set ever changed. Producers now set this directly; consumers just read it."""
...
class CompositeEmitter(EventEmitter):
    async def emit(self, event):
        last_exc = None
        for emitter in self._emitters:
            try: await emitter.emit(event)
            except Exception as exc: last_exc = exc   # ALL sinks get the event
        if last_exc is not None: raise last_exc       # raise only AFTER fan-out
```

**Flow:** Agent emits BOTH legacy and AG-UI aliases at the SAME call sites (`_AG_UI_ALIASES` table in agent/__init__.py — never instead-of) → legacy-matching consumers see zero change; AG-UI frontends consume the additive vocabulary → unknown event types are IGNORED by SSEEventEmitter so REASONING_* additions can't break legacy sinks → TOOL_RESULT/TOOL_BLOCKED both carry `payload["status"]` for the single-field blocked-vs-done read.
**Invariant:** (1) New dialects are ADDITIVE aliases fired alongside legacy types at identical call sites — a replacing migration breaks every legacy consumer. (2) Consumers must read `status`, never re-derive blockedness from payload key sets — the key-sniffing inference is the exact bug this field deleted (three silent-break copies). (3) CompositeEmitter delivers to EVERY sink even when early ones raise; errors surface only after full fan-out — short-circuiting drops events from later backends.
**Probe:** `backend/python/tests/unit/agents/adapter/test_sse_bridge.py` (:333–341, :478 — TOOL_BLOCKED events asserting `"status": ToolCallStatus.BLOCKED` on the wire); `tests/unit/agents/adapter/test_agui_emitter.py` (alias mapping); `tests/unit/agent_loop_lib/events/emitters/test_logging.py` (emitter contract).
**Retrieve:**
```bash
codebase-memory-mcp cli search_graph '{"project":"mnt-hdd-utopia-inspo-platforms-pipeshub-ai","query":"EventType ToolCallStatus CompositeEmitter TOOL_UNAVAILABLE","detail":"ids","limit":5}'
```

## Verdict
Adopt additive-dialect aliasing, the explicit status field over key-sniffing, and all-sinks-then-raise composite fan-out. Adapt your enum vocabulary but keep old+new firing together through one migration generation. Omit the AG-UI naming history once your frontend settles. Direct tests cover status-on-wire and aliasing.
