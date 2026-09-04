<!-- capsule-v2 -->
# Group chat manager state ladder — one authoritative history, deep-copied per decision

**Source:** Microsoft semantic-kernel MIT `main@b39d95a34435f4c1d55dd00c86120ce118d847e1`; Codebase Memory `semantic-kernel`. **Question:** Who owns the group-chat history, how does the manager decide user-input vs terminate vs next-speaker, and where does the round counter live?

## GroupChatManagerActor + GroupChatManager
**Path/Symbol:** `python/semantic_kernel/agents/orchestration/group_chat.py:GroupChatManagerActor._handle_response_message` (lines 293–304), `_determine_state_and_take_action` (306–368), `_call_human_response_function` (370–381); `GroupChatManager.should_terminate` (211–227), `RoundRobinGroupChatManager.select_next_agent` (247–253); `GroupChatAgentActor._handle_request_message` (172–188).
**Signature:** `async def _determine_state_and_take_action(self, cancellation_token: CancellationToken) -> None`; `async def should_terminate(self, chat_history: ChatHistory) -> BooleanResult`; `async def select_next_agent(self, chat_history: ChatHistory, participant_descriptions: dict[str, str]) -> StringResult`.
**Data Shape:** Manager is a pydantic `KernelBaseModel` with `current_round: int = 0`, `max_rounds: int | None`, `human_response_function`. Manager result types are concrete subclasses (`BooleanResult`, `StringResult`, `MessageResult`) of `GroupChatManagerResult[T]` — generic type parameters are stripped because model services reject class names like `GroupChatManagerResult[bool]` in structured-output schemas.

### Decisive source
```python
# manager actor: non-USER responses get a synthetic transfer marker FIRST
async def _handle_response_message(self, message: GroupChatResponseMessage, ctx: MessageContext) -> None:
    if message.body.role != AuthorRole.USER:
        self._chat_history.add_message(ChatMessageContent(
            role=AuthorRole.USER, content=f"Transferred to {message.body.name}"))
    self._chat_history.add_message(message.body)
    await self._determine_state_and_take_action(ctx.cancellation_token)

# the decision ladder — every manager call sees a deep-copied SNAPSHOT
async def _determine_state_and_take_action(self, cancellation_token: CancellationToken) -> None:
    should_request_user_input = await self._manager.should_request_user_input(
        self._chat_history.model_copy(deep=True))
    if should_request_user_input.result and self._manager.human_response_function:
        user_input_message = await self._call_human_response_function()
        self._chat_history.add_message(user_input_message)
        await self.publish_message(GroupChatResponseMessage(body=user_input_message), ...)
    should_terminate = await self._manager.should_terminate(self._chat_history.model_copy(deep=True))
    if should_terminate.result:
        if self._result_callback:
            result = await self._manager.filter_results(self._chat_history.model_copy(deep=True))
            result.result.metadata["termination_reason"] = should_terminate.reason
            result.result.metadata["filter_result_reason"] = result.reason
            await self._result_callback(result.result)
        return
    next_agent = await self._manager.select_next_agent(
        self._chat_history.model_copy(deep=True), self._participant_descriptions)
    await self.publish_message(GroupChatRequestMessage(agent_name=next_agent.result), ...)

# round counter increments INSIDE the manager's should_terminate
async def should_terminate(self, chat_history: ChatHistory) -> BooleanResult:
    self.current_round += 1
    if self.max_rounds is not None:
        return BooleanResult(result=self.current_round > self.max_rounds, ...)
    return BooleanResult(result=False, reason="No maximum rounds set.")
```

**Flow:** The manager actor owns the ONLY authoritative `ChatHistory`; agent actors keep their own
`_message_cache` copies (filled by Start/Response broadcasts) and are invoked with no additional messages.
After every response the manager runs the ladder: (1) `should_request_user_input` on a deep-copied snapshot —
if true and a `human_response_function` exists, the user message is added to history AND published so agents
see it; (2) `should_terminate` on another fresh snapshot — on terminate, `filter_results` picks the result
message and it is stamped with `termination_reason` + `filter_result_reason` metadata before the callback;
(3) otherwise `select_next_agent` picks the next speaker and a `GroupChatRequestMessage` is published — every
agent actor receives it but only the named one acts (`if message.agent_name != self._agent.name: return`).
`current_round` increments inside `should_terminate`, so the counter lives in the manager model and the
round limit is `current_round > max_rounds` (checked AFTER increment, so `max_rounds=3` gives exactly 3
agent responses). `_start` sends the start message to ALL member actors first (each caches the task), then
to the manager — so the manager's first selection cannot race ahead of agent context.
**Invariant:** Every manager decision sees an immutable snapshot (`model_copy(deep=True)`) — manager
implementations cannot mutate the authoritative history. The synthetic `Transferred to <name>` USER message
precedes every non-USER response in the manager's history. Termination metadata is written onto the RESULT
message, not the history. Members must have descriptions (constructor raises ValueError) because
`participant_descriptions` feeds `select_next_agent`.
**Probe:** `python/tests/unit/agents/orchestration/test_group_chat.py::test_invoke` (`invoke_stream.call_count == 3` for `max_rounds=3`; result is last ASSISTANT message), `test_invoke_with_human_response_function` (`user_input_count == 4` — 3 rounds + 1 initial), `test_round_robin_group_chat_manager_should_terminate` (4th call returns True), `test_invoke_with_list` (per-call message counts 2 then 3), `test_init_member_without_description_throws`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "semantic-kernel", query: "GroupChatManagerActor _determine_state_and_take_action should_terminate select_next_agent filter_results model_copy", limit: 10, fields: ["signature", "name", "file"] });
```
(Not executable this pass — MCP surface absent; query kept byte-for-byte for the next connected pass.)

## Verdict
Adopt: single authoritative manager-owned history with deep-copied snapshots per decision, the
user-input → terminate → select ladder, synthetic transfer markers, and termination-reason metadata on the
result. Adapt the manager contract (four abstract methods) to your own selection/termination strategies —
RoundRobin is only the default. Omit the human-response branch when your port has no HITL surface.
