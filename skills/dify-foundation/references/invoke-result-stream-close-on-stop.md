<!-- capsule-v2 -->
# invoke-result-stream-close-on-stop — How do you stop tokens from a provider mid-stream?

**Source:** dify Apache-2.0 `main@8bdf702f`; Codebase Memory `ext-dify`. **Question:** What must happen to the LLM generator when the task is cancelled while streaming?

## Explicit generator close inside the except, then re-raise
**Path/Symbol:** `api/core/app/apps/base_app_runner.py:AppRunner._handle_invoke_result_stream` (:276-369), stop arm at (:352-355).
**Signature:** `_handle_invoke_result_stream(invoke_result: Generator[LLMResultChunk], queue_manager, agent: bool, message_id/user_id/tenant_id: str | None)`.
**Data Shape:** Consumes provider chunks; accumulates `text` from str or TextPromptMessageContent list content; captures first-seen `model`/`prompt_messages` and last non-null `usage`; publishes QueueLLMChunkEvent (or QueueAgentMessageEvent when agent=True) per chunk.

### Decisive source
```python
try:
    for result in invoke_result:
        if not agent:
            queue_manager.publish(QueueLLMChunkEvent(chunk=result), PublishFrom.APPLICATION_MANAGER)
        else:
            queue_manager.publish(QueueAgentMessageEvent(chunk=result), PublishFrom.APPLICATION_MANAGER)
        ...  # text accumulation + multimodal image side-channel
except GenerateTaskStoppedError:
    # Explicitly close provider stream to stop in-flight token generation ASAP.
    invoke_result.close()
    raise

if usage is None:
    usage = LLMUsage.empty_usage()
```

**Flow:** chunk loop → publish each → accumulate text/usage → on stop (the queue listener raised GenerateTaskStoppedError through into this consumer) → `close()` the provider generator (throws GeneratorExit INTO it so its HTTP connection teardown runs now, not at GC) → re-raise so the worker's error taxonomy treats it as cancelled. Normal completion ends with a synthesized QueueMessageEndEvent carrying accumulated usage.
**Invariant:** Close happens BEFORE the raise — order matters, because unwinding without close leaves the socket draining until finalization; usage defaults to `empty_usage()` only on NORMAL completion (cancelled runs never publish end events); agent vs plain routing is per-chunk, not per-stream.
**Probe:** `grep -c 'invoke_result.close()' core/app/apps/base_app_runner.py` → 1; direct test `tests/unit_tests/core/app/apps/test_base_app_runner.py::test_handle_invoke_result_stream_closes_generator_when_stopped` (asserts close called AND exception propagates).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-dify", query: "AppRunner _handle_invoke_result_stream GenerateTaskStoppedError close", limit: 10 });
```

## Verdict
Adopt close-then-reraise for any cancellable upstream generator. Adapt the event types and accumulation rules to your protocol. Omit the multimodal branch (separate capsule).
