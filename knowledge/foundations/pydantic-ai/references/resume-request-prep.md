<!-- capsule-v2 -->
# ModelRequestNode._prepare_resume_request — how does a paused turn resume without double-counting history?

**Source:** pydantic-ai MIT `main@b3cdbc96796f0294f1ac6943cdba70d14af8a0ef`; Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** When history ends in a suspended `ModelResponse`, how is the resuming request assembled so the suspended tail stays on the wire but NOT in the run's recorded new messages?

## Resume-path request prep
**Path/Symbol:** `pydantic_ai_slim/pydantic_ai/_agent_graph.py:ModelRequestNode._prepare_resume_request` (:1625-1725), dispatched from `_prepare_request` :1463-1464 when `_resume_suspended` is set.
**Signature:** Same return tuple as `_prepare_request`; no new request to append.
**Data Shape:** `messages` returned to the model KEEP the trailing suspended `ModelResponse` (the innermost `model_request` helpers split it off as the continuation seed, so it also crosses a durable-exec boundary as part of the messages); `ctx.state.message_history` is rewound to `base_messages` WITHOUT it.

### Decisive source
```python
# _agent_graph.py:1687-1699 — wire keeps the tail; bookkeeping drops it
if not (
    messages
    and isinstance(suspended := messages[-1], _messages.ModelResponse)
    and suspended.state == 'suspended'
):
    raise exceptions.UserError('Processed history must end with a suspended `ModelResponse` to resume.')

model_request_parameters = _with_outgoing_reveal_state(model_request_parameters, messages)

# History bookkeeping operates on the base history ending in the ModelRequest that
# triggered the turn; the request messages keep the suspended tail (the continuation
# loop in the innermost helpers re-appends it to the wire history itself).
base_messages = messages[:-1]

# :1701-1719 — resumed_request = the request that TRIGGERED the paused turn (found by a
# reverse scan for the last ModelRequest), not the synthetic one; new_messages() then
# yields just the completed (merged) response.
for index in range(len(base_messages) - 1, -1, -1):
    if isinstance(message := base_messages[index], _messages.ModelRequest):
        ctx.deps.resumed_request = message
        ctx.deps.resumed_request_index = index
        break

ctx.state.message_history[:] = base_messages   # slice assign: capture_run_messages alias
ctx.deps.new_message_index = _first_new_message_index(
    base_messages, ctx.state.run_id,
    resumed_request=ctx.deps.resumed_request,
    resumed_request_index=ctx.deps.resumed_request_index)
```

**Flow:** (1) `run_step += 1`; refresh capability ids + discovered names. (2) build/replace run_context; `tool_manager.for_run_step`. (3) instructions are **rehydrated from the recorded `ModelRequest` via `_get_history_instructions`** — never re-evaluated, because a continuation completes the same logical turn and providers like Anthropic require the exact prior history back (`instruction_parts` wrapped in a single static part). (4) `_prepare_request_parameters` + settings + `before_model_request` hook, identical to the fresh path. (5) validate the tail is a `'suspended'` response; derive reveal state from the full list INCLUDING the tail. (6) split off the tail for bookkeeping; reverse-scan pin the triggering request; slice-assign history to base; derive `new_message_index`. (7) record `last_max_tokens`/`last_model_request_parameters`, check usage limits, return.

**Invariant:** The suspended response exists in exactly one of two lists at any moment: on the wire (returned `messages`) during the continuation call, or nowhere while recorded (history holds only up to the triggering request; `_finish_handling` appends the final merged response after it). Hooks see the true echo-back history (ending in the suspended response); the run result sees only the merged completion as new. Instructions are rehydrated verbatim, not re-derived — re-evaluating dynamic prompts mid-turn would change history a provider requires byte-identical.

**Probe:** `tests/models/test_streamed_continuation.py::test_resume_from_trailing_suspended_history` (:524, hooks fire once around the chain) and `::test_resume_history_without_preceding_request` (:787, error path); `tests/test_agent.py::test_agent_run_id_fresh_on_deferred_resume` (:4052).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pydantic-ai", query: "_prepare_resume_request _get_history_instructions _resume_suspended", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the seed-split discipline: wire keeps the suspended tail, recorded history drops it, and the resume pin points at the turn's ORIGINAL request found by reverse scan. Adopt verbatim instruction rehydration for continuations. Adapt the graph-context plumbing (`GraphRunContext`, capability refresh) to your host. Omit nothing else — the dual-list discipline is the whole seam. Coverage clean at the pinned commit.
