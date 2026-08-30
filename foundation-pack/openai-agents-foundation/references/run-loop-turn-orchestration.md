<!-- capsule-v2 -->
# Run-loop turn orchestration — how does one turn flow from prepared input to a SingleStepResult without duplicating streamed items?

**Source:** OpenAI Agents Python MIT `main@cb8a2e7e`; Codebase Memory project `openai-agents-python` (28,011 nodes). **Question:** When porting the per-turn engine, what is the exact ordering of hook pairs, input preparation, tracker marks, and stream-event dedup that a porter must reproduce?

## Turn spine (`run_single_turn`, `run_single_turn_streamed`, `get_new_response`)
**Path/Symbol:** `src/agents/run_internal/run_loop.py:` `run_single_turn_streamed` (1873–2217), `run_single_turn` (2220–2348), `get_new_response` (2351–2490).
**Signature:** `async def run_single_turn(*, bindings: AgentBindings[T], all_tools, original_input, generated_items, hooks, context_wrapper, run_config, should_run_agent_start_hooks, tool_use_tracker, ...) -> SingleStepResult`.
**Data Shape:** inputs are immutable-ish lists of `RunItem`/input dicts plus shared mutable `RunContextWrapper` (usage, approvals) and `AgentToolUseTracker`; output is `SingleStepResult{pre_step_items, new_step_items, session_step_items?, processed_response, next_step, original_input, model_response}`.

### Decisive source
```python
handoffs = await get_handoffs(execution_agent, context_wrapper)
all_tools, handoffs = resolve_tool_name_collisions(
    all_tools, handoffs, collision_policy=run_config.tool_name_collision_policy,
)
...
if server_conversation_tracker is not None:
    server_conversation_tracker.validate_pending_input_filter(filtered.input)
    server_conversation_tracker.mark_input_as_sent(filtered.input)
...
async with aclosing(model_run_context_stream(retry_stream, tool_use_tracker)) as model_events:
    async for event in model_events: ...
```

**Flow:** (1) `turn_input` parsed defensively (`except Exception: []`) onto `context_wrapper.turn_input`; (2) agent-start hooks via `gather_with_cancel(run_hooks, agent_hooks)` — runs once per agent, flag reset after first turn; (3) system prompt + prompts fetched concurrently; (4) **collision resolution mutates `all_tools`/`handoffs` BEFORE model exposure and span metadata**; (5) input assembled — server-tracked turns use `tracker.prepare_input(original, generated)` deltas, local sessions use `_prepare_turn_input_items` (caller items + continuation under reasoning-id policy); (6) `call_model_input_filter` applied, then `deduplicate_input_items_preferring_latest`; (7) `on_llm_start` hooks; (8) model call inside `model_run_context(tool_use_tracker)` with retry wrapper; (9) success ladder `mark_input_as_sent` → `mark_input_as_accepted` → `track_server_items(response)`; (10) `on_response_accepted` fires twice — once with `None` immediately after the raw response, again after processing with the `ProcessedResponse`; (11) `get_single_step_result_from_response` runs tools/approvals with injected `after_invocation_validation` and `before_side_effects` callbacks; (12) streaming variant filters already-emitted items by `_stream_event_item_occurrence_key` (uuid4 hex stashed as an attribute on the RunItem) before emitting step items.

**Invariant:** A streamed item must never reach the queue twice: items emitted live during the model stream get an occurrence key; when `processed_response.new_items` are emitted post-processing they are filtered against `emitted_model_item_occurrence_keys`, while the RETURNED `SingleStepResult` keeps the unfiltered list (the filter applies only to the queued copy via `dataclasses.replace`). Raising out of the stream loop leaves generators suspended — hence explicit `aclosing`.

**Probe:** `tests/test_agent_runner_streamed.py::test_streaming_resume_with_session_does_not_duplicate_items` (:2192) — resumed streamed runs must not re-emit session items; `tests/test_stream_events.py:479` pins `message_output_created` emission order.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openai-agents-python", query: "run_single_turn_streamed occurrence key collision resolve", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the ordering contract (hooks → collisions → prepare/filter/dedupe → send-marks → response-accepted twice → process) and the occurrence-key dedup; adapt `OpenAIServerConversationTracker` calls to whatever server-state mechanism your host has (skip entirely for purely local history); omit the Responses-API-specific `prompt` config plumbing unless targeting that API.
