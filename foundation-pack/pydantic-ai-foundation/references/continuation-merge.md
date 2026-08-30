<!-- capsule-v2 -->
# Continuation-chain merge — stitching provider-suspended turns into one response

**Source:** pydantic-ai (MIT) `main@b3cdbc96796f0294f1ac6943cdba70d14af8a0ef`; Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** When a model response arrives `state='suspended'` (Anthropic `pause_turn`, OpenAI background mode), how does the runtime echo it back, cap the loop, price segments, and merge them into ONE response without double-counting usage?

## model_request continuation loop
**Path/Symbol:** `pydantic_ai_slim/pydantic_ai/_agent_graph.py:model_request` (911-1040), `_split_resume_seed` (859-872), `_check_continuation_usage` (875-893).
**Signature:** `async model_request(model, *, request_context, run_context, on_progress) -> ModelResponse`.
**Data Shape:** seed = trailing suspended `ModelResponse` split off the request messages; per-segment responses carry `provider_response_id`, `state`, `usage`; two counters (`accumulate_count`, `replace_count`) classified by `merge_mode(response, new_response)`.

### Decisive source
```python
base_messages, seed = _split_resume_seed(request_context.messages)
# seed = trailing suspended ModelResponse; it is echoed back, NOT part of base history
while True:
    if response is None: messages = base_messages
    elif response.state == 'suspended':
        # TWO independent ceilings:
        if last_mode == 'replace-same-id':            # re-polling one background job
            replace_count += 1; over_limit = replace_count > MAX_BACKGROUND_POLLS
        else:                                          # fresh generation re-suspension
            accumulate_count += 1; over_limit = accumulate_count > MAX_GENERATION_CONTINUATIONS
        if over_limit: await cancel_suspended_job(model, response); raise UnexpectedModelBehavior(...)
        if delay := model.continuation_delay(response): await sleep(delay)  # cancel-safe
        messages = [*base_messages, response]          # ECHO the suspended tail back
    else: return response                              # complete -> done

    try: new_response = await model.request(messages, ...)
    except BaseException:                               # incl. CancelledError/KeyboardInterrupt
        if response is not None: await cancel_suspended_job(model, response); raise

    fill_response_cost(response); fill_response_cost(new_response)  # price PER SEGMENT
    last_mode = merge_mode(response, new_response)      # classify BEFORE merging
    response = merge_responses(response, new_response)  # parts + usage merged into one
    try: _check_continuation_usage(run_context, response.usage)   # provisional total
    except BaseException:
        if response.state == 'suspended': await cancel_suspended_job(model, response)
        raise
    on_progress(response)
```

**Flow:** strip trailing suspended seed from base history → loop: echo the suspended response as the conversation tail → request → on suspension classify the transition and check the matching ceiling → on completion merge parts+usage into a single response → commit usage exactly once at append time (never per segment). Every exit path that leaves a server-side job alive calls `cancel_suspended_job` first — including CancelledError during the inter-poll sleep.
**Invariant:** (a) The suspended tail is echoed, never duplicated into base history. (b) Usage is committed once for the whole chain (provisional deepcopy checks run mid-loop to fail fast). (c) Per-segment pricing happens before merging so tiered rates apply per request. (d) The two-ceiling rule: unbounded fresh re-suspensions get a small cap, same-id background polls a generous one. (e) No path may leak a live server-side job — cancellation precedes every raise.
**Probe:** `tests/test_agent.py::test_continuation_merges_parts_and_usage_across_response_ids` (13920), `test_continuation_request_reuses_history_instructions` (13896), `test_check_continuation_usage_without_limits` (13992), delay/retry variants at 14019-14124.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pydantic-ai", query: "model_request merge_responses cancel_suspended_job MAX_BACKGROUND_POLLS merge_mode", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the dual-ceiling loop, echo-don't-duplicate seeding, per-segment pricing, and cancel-before-raise discipline; adapt `merge_responses`/`merge_mode` to your message classes; omit the provider-specific `pause_turn`/background-mode details. The streamed twin is `_ContinuationStreamedResponse` via `model_request_stream` (1043-1102) — same ceilings, lazy segment open, OTel context captured for span continuity, teardown `aclose()` deliberately does NOT cancel server jobs (that stays on `AgentStream.cancel()`). Coverage clean.
