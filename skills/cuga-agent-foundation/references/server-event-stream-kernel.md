<!-- capsule-v2 -->
# SSE event-stream kernel — how does an HTTP stream stay cancellable mid-agent-step without corrupting checkpointed state?

**Source:** cuga-agent Apache-2.0 `main@5de53ade77c36166da6ace906af488b2b445454f`; Codebase Memory `mnt-hdd-utopia-inspo-cuga-agent`. **Question:** How do I drive a LangGraph agent behind an SSE endpoint where the client can stop generation at ANY await point, followups rehydrate prior state, and tool-call turns loop without re-running the planner?

## event_stream: stop-race, rehydration ladder, buffer-then-batch persistence
**Path/Symbol:** `src/cuga/backend/server/main.py:event_stream` (1540–2050+) with `_next_event_or_stop` (1501–1524) and `apply_request_user_context` (1527–1537).
**Signature:** `async def event_stream(query, api_mode=False, resume=None, thread_id=None, agent=None, disable_history=False, user_id=DEFAULT_USER_ID, user_attachments=None)` — yields formatted SSE strings.
**Data Shape:** per-thread `app_state.stop_events: dict[str, asyncio.Event]` (cleared on new stream); per-turn `stream_events_buffer: list[{event_name, event_data, timestamp, sequence}]` starting at sequence 0 — the DB layer owns cumulativeness; AgentLoopAnswer carries flags `end/interrupt/has_tools/flow_generalized`.

### Decisive source
```python
async def _next_event_or_stop(stream, stop_event):
    if stop_event and stop_event.is_set(): return None, True
    next_task = asyncio.create_task(stream.__anext__())
    tasks = [next_task] + ([asyncio.create_task(stop_event.wait())] if stop_event else [])
    done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
    for p in pending: p.cancel()
    ...
# tool-turn continuation: mutate checkpointer, then RECREATE the generator
run_agent.graph.update_state({"configurable": {"thread_id": thread_id}}, local_state.model_dump())
agent_stream_gen = agent_loop_obj.run_stream(state=None)   # state=None ⇒ LangGraph re-reads checkpoint
break                                                       # back to the outer while-loop
```

**Flow:** ensure/reset stop event → rehydrate state: non-resume + thread_id ⇒ get_state→AgentState(**values)→apply_message_sliding_window (fallback fresh default_state on ANY error); resume ⇒ get_state but pass state=None to run_stream → stamp user_id/service_scope via apply_request_user_context (kept un-inlined so tests exercise the real helper) → non-api_mode page step fills elements/read_page/url → buffer UserMessage(raw text + attachments) → slash soft-dispatch may rewrite local_state.input to planner_input (display keeps raw utterance) → knowledge ctx + citation-ledger rehydration + upload ctx → AgentLoop(...) → run_stream → loop: outer stop-check yields Stopped; inner race yields Stopped on stop-first, returns on done; AgentLoopAnswer dispatch (flow_generalized ⇒ restart save_reuse + chat cleanup/setup; interrupt && !has_tools ⇒ sync state, return; end ⇒ WXO plain text vs JSON payload {data, variables, active_policies, sources}, buffer Answer, batch-save [events_only when disable_history], yield); has_tools ⇒ yield tool_call, AgentRunner feedback, update_state(model_dump), recreate generator; other events buffered unless ChatAgent; malformed StreamEvent blocks logged-and-skipped.
**Invariant:** cancellation must be observable between every yielded event WITHOUT killing the LangGraph runnable mid-step (stop wins the FIRST_COMPLETED race, pending tasks cancelled); the persisted stream-events row stays cumulative across turns because the caller buffers only THIS turn and save_stream_events appends+renumbers; a malformed event must degrade, not end the stream.
**Probe:** `tests/unit/test_server_user_id_propagation.py` and `tests/unit/test_ephemeral_stream_events.py` (both executed this run: pass) pin the real-helper context propagation and the events_only persistence path.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-cuga-agent", query: "_next_event_or_stop event_stream run_stream stop_events", limit: 10 });
```

## Verdict
Adopt the stop-event race, the rehydration ladder with sliding window, turn-buffered events with DB-side append/re-sequence, and the update_state-then-recreate-generator tool loop. Adapt answer payload shapes (WXO vs default) and ChatAgent exclusion list. Omit browser-env page stepping unless you have a shared env.
