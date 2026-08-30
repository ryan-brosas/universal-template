<!-- capsule-v2 -->
# Non-streamed turn twin — is run_single_turn a faithful mirror of the streamed turn, and where exactly do the paths diverge?

**Source:** openai-agents-python MIT `main@fe45b415`; Codebase Memory `openai-agents-python`. **Question:** A porter duplicating the turn loop for a non-streaming host must know which ordering guarantees are shared and which hook/commit points are deliberately asymmetric.

## Non-streamed run_single_turn and the defer_llm_end_hooks divergence
**Path/Symbol:** `src/agents/run_internal/run_loop.py:run_single_turn` (:2377–2499) and `get_new_response` (:2508–2648).
**Signature:** `async def run_single_turn(*, bindings, all_tools, original_input, generated_items, hooks, context_wrapper, run_config, should_run_agent_start_hooks, tool_use_tracker, server_conversation_tracker=None, session=None, session_items_to_rewind=None, reasoning_item_id_policy=None, prompt_cache_key_resolver=None, error_handlers=None, agent_span=None, on_response_accepted=None, on_response_hooks_started=None, run_state=None) -> SingleStepResult`.
**Data Shape:** Same callback pair as the streamed twin (`on_response_accepted(ModelResponse, ProcessedResponse|None) -> bool`, `on_response_hooks_started()`); returns the shared `SingleStepResult`; no event queue, no `streamed_result` handle.

### Decisive source
```python
    new_response = await get_new_response(
        bindings, system_prompt, input, output_schema, all_tools, handoffs, hooks,
        context_wrapper, run_config, tool_use_tracker, server_conversation_tracker,
        prompt_config, session=session, ...,
        defer_llm_end_hooks=True,
    )

    response_accepted = False
    if on_response_accepted is not None:
        response_accepted = on_response_accepted(new_response, None)

    async def after_invocation_validation(_processed_response) -> bool:
        if response_accepted and on_response_accepted is not None:
            on_response_accepted(new_response, _processed_response)
        if response_accepted and on_response_hooks_started is not None:
            on_response_hooks_started()
        await gather_with_cancel(
            (public_agent.hooks.on_llm_end(context_wrapper, public_agent, new_response) ...),
            hooks.on_llm_end(context_wrapper, public_agent, new_response),
        )
        return response_accepted
```

**Flow:** (1) `turn_input` built with `ItemHelpers.input_to_new_input_list` (exception → empty list) and stored on `context_wrapper.turn_input`; (2) `should_run_agent_start_hooks` gates the `on_agent_start ∥ agent.hooks.on_start` gather; (3) system prompt + prompt config fetched concurrently; (4) handoffs resolved, then `resolve_tool_name_collisions`; (5) `agent_span.span_data.handoffs/tools` populated when a span exists; (6) input prepared via `server_conversation_tracker.prepare_input` or `_prepare_turn_input_items`; (7) `get_new_response(..., defer_llm_end_hooks=True)` runs filter → dedupe-prefering-latest → model/settings resolution → `validate_pending_input_filter` + `mark_input_as_sent` → `on_llm_start ∥ agent on_llm_start` gather → prompt-cache-key resolution → `get_response_with_retry` inside `model_run_context`; (8) post-success tracker re-mark (`mark_input_as_sent` + `mark_input_as_accepted` + `track_server_items`) at :2632–2634; (9) `usage.add(new_response.usage)` at :2636; (10) because `defer_llm_end_hooks=True`, the inline hook block at :2638–2646 is skipped and `on_llm_end ∥ agent on_llm_end` fires instead from `after_invocation_validation` — i.e. AFTER processing, and only when the response was accepted.
**Invariant:** Both paths fire `on_llm_end` exactly once per model response, but the non-streamed path defers it past response processing (it can be skipped entirely when the response is not accepted, e.g. superseded by an interruption path), while the streamed path fires it from its own `after_invocation_validation` only after model items are queued. A porter must not "fix" this asymmetry by moving the hook before processing — downstream consumers rely on hook-after-processing ordering for the non-streamed path.
**Probe:** `tests/test_run_hooks.py::test_async_run_hooks_with_llm` (:89) and `::test_streamed_run_hooks_with_llm` (:125) — both pin exactly one `on_llm_end` per run on their respective path.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openai-agents-python", query: "run_single_turn defer_llm_end_hooks after_invocation_validation", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the shared skeleton (start hooks → prompt fetch → collision resolution → span data → input prep → filter/dedupe → sent-mark → llm-start pair → retry call → post-success re-mark → usage add) — it is byte-for-byte symmetric with the streamed path. Adapt the `defer_llm_end_hooks=True` + `after_invocation_validation` hook placement as the deliberate divergence. Omit the streamed-only pieces (event queue, occurrence-key dedupe, `_persist_stream_input_if_needed`, terminal-response assembly). Coverage caveat: Codebase Memory MCP not connected this pass; line anchors verified by direct `grep -n`/`sed` reads at HEAD fe45b415.
