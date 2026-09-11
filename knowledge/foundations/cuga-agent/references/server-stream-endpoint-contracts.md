<!-- capsule-v2 -->
# /stream, /stop, /reset endpoint contracts — what do the X-headers promise, and what may stop/reset NEVER touch?

**Source:** cuga-agent Apache-2.0 `main@5de53ade77c36166da6ace906af488b2b445454f`; Codebase Memory `mnt-hdd-utopia-inspo-cuga-agent`. **Question:** Which request headers switch agents or disable history, and why must reset never clear checkpointer state?

## Stream control endpoints: draft routing, ephemeral threads, cooperative cancel
**Path/Symbol:** `src/cuga/backend/server/main.py:stream` (2449–2499), `stop` (2502–2538), `reset_agent_state` (2541–2604); auth via `Depends(require_chat_access)`.
**Signature:** `POST /stream`, `POST /stop`, `POST /reset` — thread_id from `X-Thread-ID` header (generated UUID when absent); truthy values are `1/true/yes/on` (case-insensitive).

### Decisive source
```python
use_draft = str(request.headers.get("X-Use-Draft", "") or "").lower() in ("1", "true", "yes", "on")
disable_history = str(request.headers.get("X-Disable-History", "") or "").lower() in (...)
...
if use_draft:
    draft_state = getattr(request.app.state, "draft_app_state", None)
    if draft_state and getattr(draft_state, "agent", None): run_agent = draft_state.agent
return StreamingResponse(event_stream(..., agent=run_agent, disable_history=disable_history, ...),
                         media_type="text/event-stream")
# /stop: create-if-absent then SET the event + clear_runtime_caches(thread_id); no thread_id ⇒ set ALL events
# /reset: CLEAR the event + drop_ledger(thread_id) — comment: LangGraph state persists per thread;
#         "The client should generate a new thread_id for a fresh start" — reset deliberately does NOT
#         delete checkpointer state and does not touch the shared env/graph.
```

**Flow:** /stream resolves user from require_chat_access, reads query + attachment snapshot, picks draft only when header set AND draft graph built, delegates everything else to event_stream. /stop flips the cooperative asyncio.Event consumed by _next_event_or_stop and clears agent_spawn runtime caches for the thread (stop-all fallback for legacy clients). /reset clears the stop flag, drops the in-memory citation source ledger, clears spawn caches — and intentionally leaves checkpointer state and shared resources alone.
**Invariant:** stop is COOPERATIVE (only observed at stream yield boundaries) and idempotent (create-if-absent); reset must NOT destroy checkpointed state because a client that reuses the thread_id expects continuity — freshness is achieved by generating a NEW thread_id, never by deletion; disable_history still persists stream_events (events_only=True) so citation-ledger rehydration and reload replay keep working while the sidebar stays clean.
**Probe:** `tests/unit/test_ephemeral_stream_events.py` (`test_disable_history_saves_events_not_conversation`, executed this run) pins the X-Disable-History persistence contract.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-cuga-agent", query: "X-Use-Draft X-Disable-History stop_events clear_runtime_caches drop_ledger", limit: 10 });
```

## Verdict
Adopt header-driven draft selection with graceful fallback to prod, cooperative stop with cache clearing, and reset-as-flag-clear (never state deletion). Adapt the truthy-header parsing to your framework's conventions. Omit the stop-all backward-compat branch if you never shipped v1 clients.
