<!-- capsule-v2 -->
# Streaming persistence gates — when does a streamed turn's output reach the session store?

**Source:** OpenAI Agents Python MIT `main@cb8a2e7e`; Codebase Memory project `openai-agents-python`. **Question:** Which conditions must hold before streamed items/final output are persisted, and what is saved when an output guardrail blocks delivery?

## Persistence gate + finalizer
**Path/Symbol:** `src/agents/run_internal/run_loop.py:` `_should_persist_stream_items` (:305–314), `_finalize_streamed_final_output` (:519–633), `_save_stream_items` (:392–421), `_retained_items_for_blocked_output` consumer (:552–556).
**Signature:** `async def _should_persist_stream_items(*, session, server_conversation_tracker, streamed_result) -> bool`.
**Data Shape:** `session: Session | None`; `server_conversation_tracker` present ⇒ server owns history; `persist_before_output_guardrails: bool` selects save ordering; `on_persisted_after_guardrails: Callable[[bool], None] | None` deferred-recording callback.

### Decisive source
```python
if session is None or server_conversation_tracker is not None:
    return False
should_skip_session_save = await input_guardrail_tripwire_triggered_for_stream(streamed_result)
return should_skip_session_save is False
```
and inside the finalizer's tripwire branch:
```python
except OutputGuardrailTripwireTriggered:
    if not persist_before_output_guardrails:
        retained_items = _retained_items_for_blocked_output(items)
        if retained_items:
            await save_items(retained_items, response_id, store_setting)
    raise
```

**Flow:** gate returns False when (a) no local session, (b) a server conversation manages history, or (c) an input guardrail tripped mid-stream (the trip path has its own `persist_session_items_for_guardrail_trip`). Final-output path: optional pre-guardrail save (resume case: tool side effects already committed) → output guardrails → on tripwire save only retained side effects → on other errors persist whole turn (verdict unknown ⇒ replayable) → extend results → final save as ONE ordered batch → set `final_output`, `is_complete`, enqueue sentinel.

**Invariant:** (1) Server-managed conversations NEVER duplicate items locally — the tracker owns them. (2) A blocked final output itself is never persisted, but tool calls/outputs that already ran ARE (the next run must see the side effect rather than re-issue it). (3) Non-tripwire guardrail ERROR ≠ verdict: persist whole. (4) `asyncio.CancelledError` from a session write during immediate cancel must not surface as a recovery failure — it is stored on `streamed_result._stored_exception` so `stream_events()` surfaces it; only `after_turn` mode finishes the turn and saves.

**Probe:** `tests/test_agent_runner_streamed.py` (guardrail-timing suite, e.g. `test_stream_input_guardrail_timing.py` cited in pass 1) — tripped input guardrail skips session save; blocked-output retention exercised via stop-on-first-tool final turns.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openai-agents-python", query: "finalize streamed final output persist guardrail retained items", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the three-part gate and the tripwire-vs-error persistence asymmetry (side effects kept, rejected output dropped); adapt the cancel-mode handling to your cancellation vocabulary; omit the `store` passthrough details if your backend has no stored-response concept.
