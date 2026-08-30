<!-- capsule-v2 -->
# Supervisor turn loop — how does the group chat manager decide who speaks next, and when does the chat end?

**Source:** autogen (MIT — LICENSE-CODE) `main@027ecf0a...`; Codebase Memory `ext-autogen`. **Question:** What is the exact start→respond→select cycle, and how do termination conditions and max_turns interleave?

## RPC start, event responses, speaker-selection barrier
**Path/Symbol:** `python/packages/autogen-agentchat/src/autogen_agentchat/teams/_group_chat/_base_group_chat_manager.py` (`handle_start` :86–132, `handle_agent_response` :134–170, `_transition_to_next_speakers` :172–193, `_apply_termination_condition` :195–228).
**Signature:** `@rpc async def handle_start(self, message: GroupChatStart, ctx)`; `@event async def handle_agent_response(self, message: GroupChatAgentResponse | GroupChatTeamResponse, ctx)`; abstract `async def select_speaker(self, thread) -> List[str] | str`.
**Data Shape:** `_message_thread` (full transcript), `_current_turn`, `_active_speakers: List[str]` — names currently holding an outstanding `GroupChatRequestPublish`.

### Decisive source
```python
self._active_speakers.remove(message.name)
if len(self._active_speakers) > 0:
    # If there are still active speakers, return without doing anything.
    return                       # <-- multi-speaker barrier
if await self._apply_termination_condition(delta, increment_turn_count=True):
    return
await self._transition_to_next_speakers(ctx.cancellation_token)
```
```python
# _apply_termination_condition ordering:
stop_message = await self._termination_condition(delta)
if stop_message is not None:
    await self._termination_condition.reset()   # reset BEFORE signaling -> rerunnable team
    self._current_turn = 0
    await self._signal_termination(stop_message); return True
if increment_turn_count: self._current_turn += 1
```

**Flow:** caller RPCs `GroupChatStart` → manager relays task messages to group topic, appends thread, applies termination on the seed delta → `select_speaker(thread)` returns name(s) → for each, publish `GroupChatRequestPublish` to its personal topic + append to `_active_speakers` → each container runs its delegate and publishes its response event → manager drains deltas into the thread until `_active_speakers` empties → repeat.
**Invariant:** with N selected speakers the loop advances only after ALL N responded (barrier), so a crashed participant hangs the team rather than silently skipping a turn; termination resets the condition and turn counter BEFORE returning so the same team object can be re-`run()`; max_turns is checked only at response boundaries (`increment_turn_count=True`), never on the seed delta.
**Probe:** `python/packages/autogen-agentchat/tests/test_group_chat.py::test_round_robin_group_chat_max_turn` and `::test_round_robin_group_chat_with_resume_and_reset` (reset semantics keep the team reusable).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-autogen", query: "BaseGroupChatManager _active_speakers select_speaker _signal_termination", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the request-publish/response-event supervisor loop with an explicit outstanding-speaker set — it generalizes to round-robin, selector, swarm, and graph policies alike. Adapt selection policy freely; that's the intended seam. Omit team-event re-broadcast (`emit_team_events`) unless you stream UI events.
