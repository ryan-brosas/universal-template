<!-- capsule-v2 -->
# ModelRequestNode._prepare_request — what must a porter preserve when assembling the outgoing request while hooks may mutate the message list?

**Source:** pydantic-ai MIT `main@b3cdbc96796f0294f1ac6943cdba70d14af8a0ef`; Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** In what order do history mutation, capability hooks, cleanup, and reveal-state derivation run when preparing a model request — and which bookkeeping must survive a hook that rebuilds the message list?

## Request-prep pipeline (`_prepare_request`)
**Path/Symbol:** `pydantic_ai_slim/pydantic_ai/_agent_graph.py:ModelRequestNode._prepare_request` (:1451-1623); `SkipModelRequest` recovery in `_make_request` (:1386-1395).
**Signature:** `async def _prepare_request(ctx, *, streaming: bool) -> tuple[Model, ModelSettings | None, ModelRequestParameters, list[ModelMessage], RunContext[DepsT]]`.
**Data Shape:** Mutates `ctx.state` (message_history, run_step, usage, last_max_tokens, last_model_request_parameters) and `ctx.deps` (new_message_index, resumed_request, resumed_request_index, tool_manager); returns the wire-ready tuple consumed by `model_request`/`request_stream`.

### Decisive source
```python
# _agent_graph.py:1541-1559 — resume pin is dual-tracked BEFORE history is rebuilt
if self.is_resuming_without_prompt:
    # the trailing request that arrived via message_history IS the request being sent:
    # track by object AND by index so _first_new_message_index can exclude it however
    # capabilities/processors mutate the list
    ctx.deps.resumed_request = self.request
    ctx.deps.resumed_request_index = len(messages) - 1
elif ctx.deps.resumed_request_index is not None:
    # later steps shift the pin by the net count change; processing that REMOVED the
    # resumed request drops the positional pin but keeps object matching
    shifted = ctx.deps.resumed_request_index - (messages_before_processing - len(messages))
    ctx.deps.resumed_request_index = shifted if shifted >= 0 else None
# capture_run_messages holds this SAME list — replace contents, never rebind the reference
ctx.state.message_history[:] = messages
ctx.deps.new_message_index = _first_new_message_index(
    messages, ctx.state.run_id,
    resumed_request=ctx.deps.resumed_request,
    resumed_request_index=ctx.deps.resumed_request_index)

# :1568-1577 — reveal state derives AFTER cleanup, never from unprocessed durable history
messages = _clean_message_history(messages, repair_last_response=True)
# A processor may remove/replace availability deltas; counting stripped evidence would ship
# a "revealed" tool with no reveal on the wire.
model_request_parameters = _with_outgoing_reveal_state(model_request_parameters, messages)

# :1588-1598 — second cleanup runs ONLY if prepare_messages returned a new list
prepared = model.prepare_messages(messages, model_request_parameters)
if prepared is not messages:
    messages = _clean_message_history(prepared, repair_last_response=True)
else:
    messages = prepared
```

**Flow:** (1) stamp `self.request.timestamp`; skip `fill_run_metadata` when resuming-without-prompt; append the request; `run_step += 1`. (2) `_select_model`, refresh loaded-capability ids + discovered tool names, `build_run_context` + `replace(retry=…, max_retries=…)`. (3) `tool_manager.for_run_step` (idempotent per step — UserPromptNode may already have called it). (4) resolve instruction parts, sort them, join onto the request; raise `UserError` iff history, parts, AND instructions are all empty. (5) `_prepare_request_parameters` → settings → build `ModelRequestContext(messages=history[:])`. (6) `before_model_request` capability hook returns a possibly-replaced context; re-read all four fields from it. (7) validate non-empty + ends-with-`ModelRequest`; `fill_run_metadata` on the trailing request (processors may have left it unset). (8) dual-track the resume pin, replace history contents in place, derive `new_message_index`. (9) clean (repairing even the LAST response's dangling calls — history is definitively going out now) → derive outgoing reveal state → `model.prepare_messages` → conditional re-clean. (10) optional pre-request token counting on a deep-copied usage (input-only lower bound priced immediately), then `check_before_request`. On `SkipModelRequest` from the hook, `_make_request` repairs `new_message_index` itself (prep bailed before updating it), counts the request, and finishes with the exception's canned response.

**Invariant:** `ctx.state.message_history` must be updated by slice assignment (`[:]`) because `capture_run_messages` observes the same list object. The resume request is excluded from "new messages" by BOTH object identity/value and pinned index — either surviving a hook's reorder/removal/rebuild keeps `result.new_messages()` correct. Reveal state is computed from the post-cleanup list that actually goes on the wire, after any `prepare_messages` reshaping has been merged back.

**Probe:** `tests/test_tool_search.py::test_prepare_request_resolves_tool_visibility` (:7291) and `::test_prepare_request_stamps_visibility_on_the_plain_path` (:7334) drive real `prepare_request` through this graph path; `tests/models/test_streamed_continuation.py::test_resume_hook_dropping_suspended_response_errors` (:823) pins the hook-mutation validation on the resume variant.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pydantic-ai", query: "_prepare_request _first_new_message_index _clean_message_history _with_outgoing_reveal_state", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the ordering contract: hooks mutate FIRST, then validation, then in-place history swap with dual resume pins, then cleanup → reveal-state derivation → per-model `prepare_messages` with an identity-guarded second clean. Adapt the capability-hook names and `_first_new_message_index` bookkeeping to your host's run-result API. Omit the token-count pricing branch if your host has no cost model. Coverage clean on all cited paths (graph + on-disk source identical at the pinned commit).
