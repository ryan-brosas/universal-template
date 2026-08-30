<!-- capsule-v2 -->
# Max-turns error handler — how does a configured handler turn MaxTurnsExceeded into a validated final output?

**Source:** OpenAI Agents Python MIT `main@cb8a2e7e`; Codebase Memory project `openai-agents-python`. **Question:** What must a porter reproduce so an exhausted turn budget can still produce a legitimate, guardrailed, optionally-persisted answer instead of raising?

## Handler resolution + deferred recording
**Path/Symbol:** `src/agents/run_internal/run_loop.py:` max-turns block in `start_streaming` (:1460–1549), `finalize_max_turns_handler_output` (:728–772); helpers `validate_handler_final_output`, `format_final_output_text`, `create_message_output_item` from `error_handlers.py`; non-streaming twin lives in the runner.
**Signature:** `async def finalize_max_turns_handler_output(*, agent, hooks, run_config, output, context_wrapper, output_guardrail_results, save_items_after_guardrails, include_in_history) -> tuple[Any, RunItem]`.
**Data Shape:** handler result carries `final_output: Any` + `include_in_history: bool`; synthesized item is a plain assistant message built from formatted text; `_record_max_turns_handler_output(publish_events: bool)` closure defaults-bound to avoid late-binding.

### Decisive source
```python
if handler_result is None:
    if handler_configured:
        streamed_result._max_turns_handled = False
    streamed_result._event_queue.put_nowait(QueueCompleteSentinel())
    break
...
await _finalize_streamed_final_output(
    ..., save_items=_save_max_turns_items,
    items=[synthesized_item] if include_in_history else [],
    response_id=None,
    persist_before_output_guardrails=False,
    on_persisted_after_guardrails=_record_max_turns_handler_output,
)
```

**Flow:** on `current_turn > max_turns`: attach span error → raise-site builds `MaxTurnsExceeded` → if no handler configured, enqueue sentinel and break (stream ends "complete" but flagged unhandled) → else persist stream input first (`_persist_stream_input_if_needed`) → validate output against the agent's schema → format text → synthesize message item → run final-output hooks → run OUTPUT GUARDRAILS (tripwire re-raises; ordinary errors still attempt the save so history stays replayable) → only after persistence succeed does the deferred callback append the synthesized item into model-input/new-item lists and publish it as a stream event → set `_max_turns_handled=True`, clamp `current_turn`/state to `max_turns`, break.

**Invariant:** The handler's output is subject to exactly the same validation and guardrails as a model-produced final output — never a bypass. History inclusion is the author's explicit choice; recording happens only after durable persistence (no phantom assistant turns when the save fails). A handler that itself returns None re-raises the original failure path.

**Probe:** `tests/test_max_turns.py` — pins exceeded-budget behavior incl. handler outcomes.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openai-agents-python", query: "max turns exceeded handler finalize", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt validate-guardrail-persist-record ordering for any budget-exhaustion escape hatch; adapt the handler registry shape (`RunErrorHandlers["max_turns"]`) freely; omit span attachment details if you lack tracing.
