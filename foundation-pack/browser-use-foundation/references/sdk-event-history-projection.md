<!-- capsule-v2 -->
# SDK event-sourcing projection — how do you rebuild a step-by-step agent history from a flat stream of transport events?

**Source:** browser-use MIT `main@3c989dc`; Codebase Memory `browser-use`. **Question:** how do you turn `{event_type, payload, seq}` records (from a response body OR live notifications) into `AgentOutput` + per-tool `ActionResult` history items that downstream consumers can't distinguish from native steps?

## Connected graph-selected seam
**Path/Symbol:** `browser_use/beta/service.py` — turn slicing `_terminal_turn_spans` (:2652), call collection `_tool_started_calls` (:2042) / `_tool_calls_with_final_done` (:2064), result folding `_tool_results_by_call_id` (:2088) / `_unkeyed_tool_results` (:2171) with merge predicates `_is_redundant_paired_output_delta` (:2000) and `_matching_unkeyed_tool_result_index` (:2300); output synthesis `_model_output_from_tool_calls` (:2532) via pydantic `create_model`; assembly `_history_items_from_terminal_turns` (:2669).
**Signature:** `_history_items_from_terminal_turns(events, *, started, finished, final_result, attachments, failure, is_done) -> list[AgentHistory] | None`.
**Data Shape:** events carry `event_type`, optional `seq`/`ts_ms`, and a dict `payload`; tool calls appear as `tool.started`/`model.tool_call`/`model.response.output_item`(type `function_call`) with `tool_call_id`; results as `tool.output`/`tool.output_delta`/`exec_command.end`/`tool.failed`/`tool.aborted`/`tool.finished`/`command.waiting`/`browser_script.*`.

### Decisive source
```python
# one history item per model.turn.request span:
starts = [i for i,e in enumerate(events) if _event_type(e)=='model.turn.request']
spans  = [(s, starts[k+1] if k+1<len(starts) else len(events)) for k,s in enumerate(starts)]
# delta streams CONCATENATE into one text; terminal events REPLACE by call id:
if event_type in _TOOL_OUTPUT_DELTA_EVENTS:
    if previous is not None and previous[0] not in (*_TOOL_OUTPUT_DELTA_EVENTS, 'tool.finished'): continue
    merged_payload['text'] = f'{previous_text}{delta_text}'   # append
...
if event_type == 'tool.finished' and previous is not None and previous[0] != 'tool.finished': continue
results[key] = (event_type, payload)                          # last-writer-wins
# synthetic dynamic action schema — the Rust core's tools aren't known to Python:
action_fields = {name: (dict[str,Any] | None, None) for name in action_names}
recovered = create_model('RustTerminalActionModel', __base__=ActionModel, **action_fields)
# the session-level done is INJECTED as a trailing fake tool call so history shape matches:
done_arguments = {'text': final_result, 'success': True}
if attachments: done_arguments['files_to_display'] = attachments
```

**Flow:** slice spans → collect calls in first-seen order (dedupe by call id) → fold results keyed by `tool_call_id` (deltas concatenate; `command.waiting` composes "Process running" text; `exec_command.end` only counts when it has text; `tool.failed` yields to earlier `tool.aborted`) → match unkeyed results positionally by tool name (`allow_any` ONLY for calls lacking explicit ids) → build each `AgentHistory` with synthesized `AgentOutput` (thinking/memory recovered from delta streams) and per-call `ActionResult` (error taxonomy per event type; >1000-char outputs collapse to a `<read_state>` pointer via `_terminal_tool_memory` :2436 with `_MAX_TERMINAL_LONG_TERM_TEXT_LENGTH` :1935) → inject final `done` call on the last turn only.
**Invariant:** ordering is preserved end-to-end (first-seen call order, first-seen dedupe keys); a delta must never overwrite a terminal result nor be double-counted when both raw and paired delta arrive (`_is_redundant_paired_output_delta`: same stream + session + suffix ⇒ skip); failures attach to the exact call, never the session.
**Probe:** `tests/ci/test_beta_agent.py:1367` `test_rust_history_applies_terminal_session_rollback` (asserts per-turn memory list `['First turn','Third turn']` and rolled-back turn absent); `tests/ci/test_beta_agent.py:6405` `test_rust_history_uses_browser_script_lifecycle_outputs_as_result`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "browser-use", query: "_history_items_from_terminal_turns _tool_results_by_call_id create_model RustTerminalActionModel", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt span-per-turn reconstruction + keyed-result folding + injected synthetic `done` whenever you must project an event log into an actions-and-results history; adapt the event-type vocabulary and the memory-collapse threshold; omit the browser_script/exec_command specifics unless your core emits them.
