<!-- capsule-v2 -->
# Swarm handoff state machine — what makes control transfer purely a message scan?

**Source:** autogen (MIT — LICENSE-CODE) `main@027ecf0a...`; Codebase Memory `ext-autogen`. **Question:** How does the swarm manager pick the next speaker without any model call, and what validation protects resumed sessions?

## Last-handoff-wins over a reversed thread walk
**Path/Symbol:** `python/packages/autogen-agentchat/src/autogen_agentchat/teams/_group_chat/_swarm_group_chat.py` (`validate_group_state` :47–73, `select_speaker` :82–98, `reset` :75–80).
**Signature:** `async def select_speaker(self, thread: Sequence[BaseAgentEvent | BaseChatMessage]) -> List[str] | str`.
**Data Shape:** State = `_current_speaker` (initialized to `participant_names[0]`) + inherited `_message_thread`. Handoffs are `HandoffMessage{target, content, source}` messages; agents emit them via tool calls or direct returns.

### Decisive source
```python
if len(thread) == 0:
    return [self._current_speaker]
for message in reversed(thread):
    if isinstance(message, HandoffMessage):
        self._current_speaker = message.target
        assert self._current_speaker in self._participant_names
        return [self._current_speaker]
return self._current_speaker      # no handoff seen -> current speaker keeps the floor
```
```python
# validate_group_state: only the LATEST handoff must be valid -- do not look past it
for existing_message in reversed(self._message_thread):
    if isinstance(existing_message, HandoffMessage):
        if existing_message.target not in self._participant_names:
            raise ValueError(f"The existing handoff target {existing_message.target} is not one of the participants ...")
        # The latest handoff message should always target a valid participant.
        return
```

**Flow:** manager's turn → scan thread backwards for the newest `HandoffMessage` → target becomes current speaker (sticky across handoff-less turns) → request-publish goes to exactly that participant. Resuming with a task containing a HandoffMessage seeds control transfer explicitly.
**Invariant:** validity of OLD handoff targets is deliberately NOT checked once a newer handoff exists (early `return`) — historical targets may legitimately reference participants pruned between sessions, but the latest one must resolve; empty-thread start always returns the FIRST participant, making participant order part of the public contract.
**Probe:** `python/packages/autogen-agentchat/tests/test_group_chat.py::test_swarm_handoff` and `::test_swarm_handoff_using_tool_calls` (handoffs via tool-call path); `tests/test_group_chat_nested.py::test_swarm_doesnt_support_nested_teams`.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-autogen", query: "SwarmGroupChatManager select_speaker HandoffMessage _current_speaker", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt last-handoff-wins scanning when you want explicit control flow with zero selection inference. Adapt validation strictness to whether participants can change mid-session. Omit nothing else — the whole policy is 17 lines.
