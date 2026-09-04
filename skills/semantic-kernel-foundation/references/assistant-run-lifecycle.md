<!-- capsule-v2 -->
# Assistant run lifecycle — server-owned run loop: poll ladder, error gate, step replay with dedupe

**Source:** Microsoft semantic-kernel MIT `main@b39d95a34435f4c1d55dd00c86120ce118d847e1`; Codebase Memory `semantic-kernel`. **Question:** How does an agent drive a server-owned assistant run to completion — polling, error handling, and message replay — without owning the tool loop?

## AssistantThreadActions.invoke run loop
**Path/Symbol:** `python/semantic_kernel/agents/open_ai/assistant_thread_actions.py:AssistantThreadActions.invoke` (lines 137–368; status sets 74–75), `_poll_run_status`/`_poll_loop` (728–768), `run_polling_options.py` (31 ln).
**Signature:** `async def invoke(cls, *, agent: "OpenAIAssistantAgent", thread_id: str, ..., polling_options: RunPollingOptions | None = None, function_choice_behavior: FunctionChoiceBehavior | None = None, **kwargs) -> AsyncIterable[tuple[bool, "ChatMessageContent"]]`.
**Data Shape:** Yields `(is_visible, ChatMessageContent)` tuples. Class-level status sets: `polling_status = ["queued", "in_progress", "cancelling"]`, `error_message_states = ["failed", "cancelled", "expired", "incomplete"]`. `RunPollingOptions` defaults: 250 ms interval, 1 s backoff after threshold 2, 1 min `run_polling_timeout`.

### Decisive source
```python
processed_step_ids = set()
function_steps: dict[str, "FunctionCallContent"] = {}

while run.status != "completed":
    run = await cls._poll_run_status(agent=agent, run=run, thread_id=thread_id,
                                     polling_options=polling_options or agent.polling_options)
    if run.status in cls.error_message_states:
        # last_error.message / incomplete_details.reason folded into one AgentInvokeException
        raise AgentInvokeException(f"Run failed with status: `{run.status}` ...")
    if run.status == "requires_action":
        fccs = get_function_call_contents(run, function_steps)
        if fccs:
            yield False, generate_function_call_content(agent_name=agent.name, fccs=fccs)
            ...  # invoke on a FRESH ChatHistory, submit_tool_outputs, continue
    steps_response = await agent.client.beta.threads.runs.steps.list(run_id=run.id, thread_id=thread_id)
    def sort_key(step):  # tool_calls first, ties by completed_at
        return (0 if step.type == "tool_calls" else 1, step.completed_at)
    completed_steps_to_process = sorted(
        [s for s in steps if s.completed_at is not None and s.id not in processed_step_ids], key=sort_key)
    for completed_step in completed_steps_to_process:
        ...  # tool_calls -> code_interpreter (visible) / function (via function_steps bridge)
        ...  # message_creation -> _retrieve_message -> yield True
        processed_step_ids.add(completed_step.id)
```

**Flow:** Create the run, then loop while status != "completed". Each iteration polls first
(`_poll_run_status` wraps `_poll_loop` in `asyncio.wait_for(..., run_polling_timeout)`; timeout →
`AgentInvokeException`). `_poll_loop` is sleep-first: sleep `get_polling_interval(count)` (250 ms
until count exceeds threshold 2, then 1 s backoff), retrieve, retry-anyway on retrieve failure,
break only when status leaves `polling_status`. A terminal error status raises one exception
carrying `last_error.message` and/or `incomplete_details.reason`. `requires_action` is handled
inline (see requires-action-tool-handoff). Otherwise the run's steps are listed and replayed:
only steps with `completed_at` and not yet in `processed_step_ids` are processed, sorted
tool_calls-first then by `completed_at`; tool_calls steps yield code-interpreter content
(visible) or function results resolved through the id-keyed `function_steps` bridge (invisible);
message_creation steps yield the retrieved message (visible). Every processed step id is added to
`processed_step_ids`, so the next poll iteration never replays it.
**Invariant:** The loop is server-owned — the client never re-invokes the model; it only polls,
submits tool outputs, and replays steps. `processed_step_ids` guarantees each step yields exactly
once across poll iterations; the sleep-first poll ladder means the first retrieve happens after
one interval, not immediately; the wait_for timeout is the only exit from a stuck run.
**Probe:** `python/tests/unit/agents/openai_assistant/test_assistant_thread_actions.py::test_assistant_thread_actions_invoke` (line 437), `test_assistant_thread_actions_stream_run_fails` (631), `test_poll_loop_exits_on_status_change` (768) — pins the poll-loop exit on status change and the failed-run exception path.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "semantic-kernel", query: "AssistantThreadActions invoke _poll_run_status _poll_loop processed_step_ids", limit: 10, fields: ["signature", "name", "file"] });
```
(Not executable this pass — MCP surface absent; query kept byte-for-byte for the next connected pass.)

## Verdict
Adopt: the poll-ladder shape (sleep-first, interval→backoff after threshold, wait_for timeout as the only stuck-run exit), the error-status gate folding last_error/incomplete_details into one exception, and the processed-id dedupe + deterministic step sort for replay. Adapt status sets and polling defaults to your provider's run model. Omit the OpenAI step-object specifics if your server streams events instead of exposing step listing.
