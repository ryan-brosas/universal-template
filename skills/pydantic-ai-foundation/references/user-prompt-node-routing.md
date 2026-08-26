<!-- capsule-v2 -->
# UserPromptNode.run — how a run's first node turns (history, prompt, deferred results) into the next graph node

**Source:** pydantic-ai (MIT) `main@b3cdbc96796f0294f1ac6943cdba70d14af8a0ef`; Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** When starting/resuming a run, in what order does UserPromptNode clean history, adopt the captured message list, reuse an unanswered request, route suspended tails and pending tool calls, and build the next ModelRequest?

## UserPromptNode.run routing ladder
**Path/Symbol:** `pydantic_ai_slim/pydantic_ai/_agent_graph.py:UserPromptNode` (501-740), `run` (523-658).
**Signature:** `async run(ctx: GraphRunContext[GraphAgentState, GraphAgentDeps]) -> ModelRequestNode | CallToolsNode`.
**Data Shape:** fields: `user_prompt`, `deferred_tool_results`, `instructions`/`instructions_functions`, `system_prompts`/`system_prompt_functions`/`system_prompt_dynamic_functions`. Mutates `ctx.state.message_history` and `ctx.deps.new_message_index`; returns the next node.

### Decisive source
```python
# 1) adopt the capture_run_messages list as THE history list
ctx_messages = get_captured_run_messages()      # LookupError -> messages = []
messages[:] = _clean_message_history(ctx.state.message_history)
ctx.state.message_history = messages            # new parts append to the captured list
ctx.deps.new_message_index = len(messages)

# 2) explicit deferred results bypass prompt handling entirely
if self.deferred_tool_results is not None:
    return await self._handle_deferred_tool_results(...)

# 3) trailing 'interrupted' request => close its response's open calls
if messages and isinstance(last := messages[-1], ModelRequest) and last.state == 'interrupted':
    messages[:] = _repair_dangling_tool_calls(messages, repair_last_response=True)

# 4) resume-without-prompt: pop last ModelRequest, REUSE its parts
if isinstance(last_message, ModelRequest) and self.user_prompt is None:
    messages.pop()
    next_message = ModelRequest(parts=last_message.parts, run_id=..., ...)

# 5) suspended tail + no prompt -> placeholder request, resume path
return ModelRequestNode(request=ModelRequest(parts=[]), _resume_suspended=last_message)
#    suspended tail + NEW prompt -> UserError (would leak the server-side job)

# 6) response tail without prompt: advance tool manager ONE step ahead,
#    pending tool calls beat instructions; nothing to send -> CallToolsNode anyway
run_context = replace(build_run_context(ctx), run_step=ctx.state.run_step + 1, ...)
ctx.deps.tool_manager = await ctx.deps.tool_manager.for_run_step(run_context)
if last_message.tool_calls: return CallToolsNode(last_message)
instruction_parts = await _get_instructions(ctx, run_context)
if not instruction_parts: return CallToolsNode(last_message)

# 7) fresh conversation: system prompts ONLY when history is empty; then user part
parts = []
if not messages: parts.extend(await self._sys_parts(run_context))
if self.user_prompt is not None: parts.append(UserPromptPart(self.user_prompt))
```

**Flow:** adopt captured list → deferred-results shortcut → interrupted-repair → (resume-without-prompt part-reuse | suspended-resume dispatch | tool-call/instruction continuation) → re-evaluate dynamic system prompts in place → build next_message → return `ModelRequestNode(request=next_message, is_resuming_without_prompt=...)`.
**Invariant:** (a) The captured `capture_run_messages()` list object must BECOME the run's history list (slice-assign + rebind), or captured messages diverge from history. (b) A trailing `'complete'` request is left alone even though its response has open calls — only `'interrupted'` tails are repaired; those calls may still receive `deferred_tool_results`. (c) Pending tool calls on a prompt-less continuation outrank instructions; if neither exists there is no model call (`CallToolsNode` still classifies/ends the run). (d) System prompts enter only on an empty history — they are not re-emitted mid-conversation; dynamic ones are refreshed by `_reevaluate_dynamic_prompts` keyed on `SystemPromptPart.dynamic_ref`. (e) A new prompt on top of a suspended response raises rather than silently abandoning the provider job.
**Probe:** `tests/test_agent.py::test_user_prompt_with_deferred_tool_results` (11021) pins results+prompt co-delivery; duplicate-result rejection at 10989; `tests/test_sanitize_messages.py:162` covers dangling-call repair semantics; `capture_run_messages` adoption pinned at `tests/test_agent.py:3814`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pydantic-ai", query: "UserPromptNode run _handle_deferred_tool_results _repair_dangling_tool_calls", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the ladder order and the list-adoption invariant (any host with a "capture what was sent" feature needs it); adapt `_repair_dangling_tool_calls` to your message classes keeping the state-conditional rule ('interrupted' repairs, 'complete' waits); omit the pydantic-ai-specific suspended-provider plumbing if your host has no server-side pause. Coverage clean.
