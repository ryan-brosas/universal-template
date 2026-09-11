<!-- capsule-v2 -->
# Participant container buffering — how do delegates see shared history without the manager serializing it?

**Source:** autogen (MIT — LICENSE-CODE) `main@027ecf0a...`; Codebase Memory `ext-autogen`. **Question:** How does a participant agent accumulate broadcast context and then hand exactly that context to its delegate on request?

## Buffer-on-broadcast, drain-on-request
**Path/Symbol:** `python/packages/autogen-agentchat/src/autogen_agentchat/teams/_group_chat/_chat_agent_container.py` (`handle_start` :56–61, `handle_agent_response` :63–66, `handle_request` :85–159, `_buffer_message` :161–165).
**Signature:** `@event async def handle_request(self, message: GroupChatRequestPublish, ctx: MessageContext) -> None`.
**Data Shape:** `_message_buffer: List[BaseChatMessage]` — filled by broadcast events (`GroupChatStart`, peers' `GroupChatAgentResponse`, nested `GroupChatTeamResponse`), consumed only by the personal-topic request. Unregistered message types raise immediately at buffer time.

### Decisive source
```python
# On GroupChatRequestPublish (personal topic):
async for msg in self._agent.on_messages_stream(self._message_buffer, ctx.cancellation_token):
    if isinstance(msg, Response):
        await self._log_message(msg.chat_message)
        response = msg
    else:
        await self._log_message(msg)
if response is None:
    raise RuntimeError("The agent did not produce a final response. ...")
self._message_buffer.clear()                     # drain ONLY after success
await self.publish_message(
    GroupChatAgentResponse(response=response, name=self._agent.name),
    topic_id=DefaultTopicId(type=self._parent_topic_type), ...)
except Exception as e:
    await self.publish_message(GroupChatError(error=SerializableException.from_exception(e)), ...)
    raise                                        # re-raise AFTER publishing the error
```

**Flow:** every chat message published to the group topic lands in each container's buffer → when the manager requests a turn, the container passes the WHOLE buffer to its delegate (`ChatAgent.on_messages_stream`, or a nested team via `run_stream(output_task_messages=False)`) → streams intermediate events to the output topic for live UI → publishes its final response back to the group topic → clears buffer.
**Invariant:** buffer is cleared only on SUCCESS — a failed turn preserves accumulated context so a retried/resumed run sees consistent history; delegate exceptions are double-reported: serialized into a `GroupChatError` broadcast AND re-raised so the runtime records the failure (embedded runtime turns that into stream termination with error).
**Probe:** `python/packages/autogen-agentchat/tests/test_group_chat.py::test_round_robin_group_chat_with_exception_raised_from_agent` (error propagation path); `tests/test_group_chat_nested.py::test_swarm_doesnt_support_nested_teams` (container/team boundary enforcement).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-autogen", query: "ChatAgentContainer handle_request _message_buffer GroupChatAgentResponse", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt buffer-on-broadcast/drain-on-request as the stateless-delegation pattern — participants need no shared memory, only idempotent buffering. Adapt buffer persistence (it round-trips through container `save_state`) if your runs span processes. Omit the streaming tap if you don't surface intermediate events.
