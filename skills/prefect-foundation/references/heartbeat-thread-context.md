<!-- capsule-v2 -->

# Heartbeat thread with copied context — How do you emit liveness events for a possibly-blocked run without losing the settings context?

**Source:** prefect Apache-2.0 `main@ce79dd3d6cfa2b7337265498210dbc4d25bcdc98`; Codebase Memory `ext-prefect`. **Question:** How do you keep emitting heartbeats while the main thread is blocked, and why must the heartbeat thread's context be explicitly copied?

## Daemon OS thread, not an asyncio task

**Path/Symbol:** `src/prefect/flow_engine.py:_send_heartbeats (306-378)`; interval floor `MINIMUM_HEARTBEAT_INTERVAL = 30 (:162)`.

**Signature:** `_send_heartbeats(engine: "BaseFlowRunEngine[Any, Any]", join_on_exit: bool = True) -> Generator[None, None, None]`.

**Data Shape:** Reads `engine.heartbeat_seconds` (property clamps settings value up to ≥30; `None` disables entirely). Pre-computes `(resource: dict[str,str], related: list[RelatedResource])` ONCE via `engine._build_heartbeat_event_template()` before starting the thread, so per-tick work is just `emit_event`.

### Decisive source
```python
# Copy the current context so the heartbeat thread sees the same
# `SettingsContext` ... Without this, `threading.Thread` starts with an empty
# context and `SettingsContext.get()` falls back to the process-wide
# `GLOBAL_SETTINGS_CONTEXT`, which is initialized at import time and can
# have a stale `api.url=None`.
heartbeat_ctx = contextvars.copy_context()
thread = threading.Thread(
    target=heartbeat_ctx.run, args=(heartbeat_loop,), daemon=True
)
...
    finally:
        stop_event.set()
        if join_on_exit:
            thread.join(timeout=2)
```

**Flow:** disabled (`None`) → bare yield → return · enabled → clamp interval ≥30 → build event template once → `stop_event = threading.Event()` → loop { stop if run state is final; try emit (exceptions logged debug, never fatal); sleep 1s × N checking stop_event each second } → on context exit: set stop_event, join(timeout=2) only when `join_on_exit=True`.

**Invariant:** (1) The thread is a daemon **OS thread**, chosen deliberately so heartbeats fire even when the event loop is blocked by CPU-bound user code — an asyncio task would starve exactly when needed. (2) `contextvars.copy_context()` before `Thread(...)` is LOAD-BEARING: a fresh thread starts with empty context, `SettingsContext.get()` then falls back to the import-time global whose `api.url` may be `None`, which spawned an ephemeral SubprocessASGIServer during teardown and aborted processes (documented regression). (3) Async engines pass `join_on_exit=False` to avoid blocking the loop on shutdown. (4) Sleep happens in 1-second increments against `stop_event` so shutdown latency ≤1s instead of a full interval. (5) A final state stops emission from INSIDE the loop (check-before-emit).

**Probe:** `grep -c 'MINIMUM_HEARTBEAT_INTERVAL' src/prefect/flow_engine.py` → 3; `grep -c 'contextvars.copy_context' src/prefect/flow_engine.py` → 1. Direct tests: `tests/test_flow_engine.py:6034 TestFlowRunEngineHeartbeat.test__send_heartbeats_clamps_low_values` (interval below 30 clamped to MINIMUM_HEARTBEAT_INTERVAL) plus `test_heartbeat_seconds_property_*` (:5990-6032) pinning clamp/pass-through/None-disabled.

## Get live surrounding code
**Retrieve:**
```bash
codebase-memory-mcp cli search_graph '{"project": "ext-prefect", "query": "_send_heartbeats heartbeat thread", "limit": 4}'
```

## Verdict
Adopt the daemon-thread + copied-context + pre-computed-template pattern verbatim for any long-running job needing liveness pings past a blocking GIL section; adapt the interval floor and event schema to your host; omit Prefect's specific event resource naming (`prefect.flow-run.<id>`, tags as related resources).
