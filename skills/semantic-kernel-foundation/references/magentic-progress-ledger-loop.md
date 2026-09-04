<!-- capsule-v2 -->
# Magentic progress-ledger loop — structured-output stall detection with replan-and-reset recovery

**Source:** Microsoft semantic-kernel MIT `main@b39d95a34435f4c1d55dd00c86120ce118d847e1`; Codebase Memory `semantic-kernel`. **Question:** How does the Magentic-One manager detect stalling through a structured progress ledger, and what exactly happens on a stall (replan, reset, limits)?

## MagenticManagerActor inner/outer loops + StandardMagenticManager
**Path/Symbol:** `python/semantic_kernel/agents/orchestration/magentic.py:MagenticManagerActor._run_inner_loop` (lines 586–660), `_check_within_limits` (695–727), `_reset_for_outer_loop` (662–672), `MagenticContext.reset` (128–132); `StandardMagenticManager.create_progress_ledger` (459–495), `__init__` validation (219–248); `MagenticAgentActor._handle_reset_message` (838–845).
**Signature:** `async def _run_inner_loop(self, cancellation_token: CancellationToken) -> None`; `async def create_progress_ledger(self, magentic_context: MagenticContext) -> ProgressLedger`; `async def _check_within_limits(self) -> bool`.
**Data Shape:** `ProgressLedger` = five `ProgressLedgerItem(reason: str, answer: str | bool)` fields: `is_request_satisfied`, `is_in_loop`, `is_progress_being_made`, `next_speaker`, `instruction_or_question`. `MagenticContext` carries `round_count`, `stall_count`, `reset_count`; `reset()` clears chat history and stall count but NOT the task, round count, or participants. Manager limits: `max_stall_count` (default 3), `max_reset_count` (None), `max_round_count` (None).

### Decisive source
```python
async def _run_inner_loop(self, cancellation_token: CancellationToken) -> None:
    within_limits = await self._check_within_limits()
    if not within_limits:
        return
    self._context.round_count += 1
    current_progress_ledger = await self._manager.create_progress_ledger(self._context.model_copy(deep=True))
    if current_progress_ledger.is_request_satisfied.answer:
        await self._prepare_final_answer()
        return
    if not current_progress_ledger.is_progress_being_made.answer or current_progress_ledger.is_in_loop.answer:
        self._context.stall_count += 1
    else:
        self._context.stall_count = max(0, self._context.stall_count - 1)
    if self._context.stall_count > self._manager.max_stall_count:
        self._task_ledger = await self._manager.replan(self._context.model_copy(deep=True))
        await self._reset_for_outer_loop(cancellation_token)   # MagenticResetMessage + context.reset()
        await self._run_outer_loop(cancellation_token)
        return
    next_step = current_progress_ledger.instruction_or_question.answer
    self._context.chat_history.add_message(ChatMessageContent(role=AuthorRole.ASSISTANT, content=next_step, ...))
    await self.publish_message(MagenticResponseMessage(body=self._context.chat_history.messages[-1]), ...)
    next_speaker = current_progress_ledger.next_speaker.answer
    if next_speaker not in self._participant_descriptions:
        raise ValueError(f"Unknown speaker: {next_speaker}")
    await self.publish_message(MagenticRequestMessage(agent_name=next_speaker), ...)

# structured output injected per-call on a CLONE of the settings
prompt_execution_settings_clone = PromptExecutionSettings.from_prompt_execution_settings(
    self.prompt_execution_settings)
prompt_execution_settings_clone.update_from_prompt_execution_settings(
    PromptExecutionSettings(extension_data={"response_format": ProgressLedger}))
response = await self.chat_completion_service.get_chat_message_content(
    magentic_context.chat_history, prompt_execution_settings_clone)
return ProgressLedger.model_validate_json(response.content)
```

**Flow:** Outer loop (`_run_outer_loop`): add the rendered task ledger to the manager's own history (the
publisher does not receive its own published message) and publish it so all agents cache it, then enter the
inner loop. Inner loop per round: limits check → round_count++ → ask the manager for a structured
`ProgressLedger` → satisfied ⇒ `prepare_final_answer` (result callback) and stop; no-progress OR in-loop ⇒
`stall_count += 1`, progress ⇒ decrement floored at 0; `stall_count > max_stall_count` ⇒ replan (facts+plan
regenerated — two extra LLM calls), publish `MagenticResetMessage` (every agent actor clears its message
cache AND deletes its agent thread), reset the context, restart the outer loop; otherwise publish the
instruction as an ASSISTANT message and request the named next speaker (unknown name ⇒ ValueError).
Limit exhaustion (`_check_within_limits`): round or reset limit hit ⇒ return the LATEST ASSISTANT message
from history as a partial result (or a synthesized "Stopped because the maximum <limit> limit was reached"
message when none exists) through the result callback, and stop. `StandardMagenticManager.__init__`
validates structured-output support eagerly: settings must have a `response_format` attribute and it must
NOT be pre-set (the manager injects it per call).
**Invariant:** The progress ledger is requested on a deep-copied context snapshot; the response_format
injection happens on a settings CLONE, never mutating the manager's base settings. Reset clears agent-side
caches and threads but never the task or round count. The stall counter is symmetric (increment on stall,
floored decrement on progress) so recovery from a transient stall does not permanently bias toward replan.
Unknown next_speaker is a hard error, not a retry.
**Probe:** `python/tests/unit/agents/orchestration/test_magentic.py::test_invoke` (2 agent invokes + 3 LLM calls for the happy path), `test_invoke_with_max_stall_count_exceeded` (`get_chat_message_content.call_count == 5` — replan adds 2), `test_invoke_with_max_round_count_exceeded` (partial result returned, 1 agent invoke, 2 LLM calls), `test_invoke_with_max_reset_count_exceeded` (4 LLM calls — plan + replan), `test_invoke_with_unknown_speaker` (ValueError), `test_invoke_with_list_error` (Magentic rejects list input).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "semantic-kernel", query: "MagenticManagerActor _run_inner_loop ProgressLedger stall_count replan MagenticResetMessage create_progress_ledger response_format", limit: 10, fields: ["signature", "name", "file"] });
```
(Not executable this pass — MCP surface absent; query kept byte-for-byte for the next connected pass.)

## Verdict
Adopt: the five-field structured progress ledger, the symmetric stall counter with replan+reset recovery,
partial-result-on-limit-exhaustion, and per-call response_format injection on a settings clone. Adapt the
prompt templates (`prompts/_magentic_prompts.py`) and the manager base class to your model surface — the
manager REQUIRES a structured-output-capable chat completion service. Omit the reset-message fan-out if your
actors hold no server-side threads.
