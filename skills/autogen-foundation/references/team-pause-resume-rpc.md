<!-- capsule-v2 -->
# Team pause/resume — how do you freeze a running multi-agent team without tearing down its run loop?

**Source:** autogen (MIT — LICENSE-CODE) `main@027ecf0a379bcc1d09956d46d12d44a3ad9cee14`; Codebase Memory project `autogen` (FULL, 16,432 nodes / 86,358 edges, generation 2026-08-24T16:12:29Z). **Question:** How does pause/resume reach every participant without terminating `run()`/`run_stream()`, and who is responsible for actually stopping work?

## Out-of-band RPC with empty markers; cooperative no-op defaults
**Path/Symbol:** `python/packages/autogen-agentchat/src/autogen_agentchat/teams/_group_chat/_base_group_chat.py` (`pause` :657–701, `resume` :703–746); markers `_events.py` :97–106; container handlers `_chat_agent_container.py` :176–192; manager handlers `_base_group_chat_manager.py` :278–286; agent defaults `agents/_base_chat_agent.py` :219–231.
**Signature:** `async def pause(self) -> None` / `async def resume(self) -> None` · `@rpc async def handle_pause(self, message: GroupChatPause, ctx: MessageContext) -> None`.
**Data Shape:** `GroupChatPause`/`GroupChatResume` are EMPTY pydantic BaseModels — the signal is the message type itself, carrying zero payload. Delivery target per participant: `AgentId(type=participant_topic_type, key=self._team_id)`, plus one to the group-chat manager.

### Decisive source
```python
# pause(): initialized-gate, then N+1 direct RPCs — participants AND manager
if not self._initialized:
    raise RuntimeError("The group chat has not been initialized. It must be run before it can be paused.")
for participant_topic_type in self._participant_topic_types:
    await self._runtime.send_message(
        GroupChatPause(), recipient=AgentId(type=participant_topic_type, key=self._team_id))
await self._runtime.send_message(GroupChatPause(), recipient=AgentId(type=self._group_chat_manager_topic_type, key=self._team_id))

# container: recursion for nested teams, delegation otherwise
if isinstance(self._agent, Team):
    await self._agent.pause()
else:
    await self._agent.on_pause(ctx.cancellation_token)

# base agent default: pausing is COOPERATIVE
async def on_pause(self, cancellation_token: CancellationToken) -> None:
    ...
    pass
```

**Flow:** team must be running (`_initialized`) → `pause()` fans one empty marker RPC to each participant + manager → each container recurses into nested Teams or calls the delegate's `on_pause(token)` → the AGENT sets its own flag and its in-flight loop observes it (`assert not self._is_paused` in the test agent) → `resume()` repeats the fan-out with `GroupChatResume`. `run`/`run_stream` stay alive throughout; participant exceptions propagate out of `pause()` itself.
**Invariant:** pause/resume never touch the run loop's control flow — termination conditions, turn counters, and the output stream are untouched; only agent-level cooperation stops work, and both the manager handler and `BaseChatAgent.on_pause/on_resume` are literal no-op defaults. Un-initialized teams raise RuntimeError instead of silently queuing markers.
**Probe:** `python/packages/autogen-agentchat/tests/test_group_chat_pause_resume.py::test_group_chat_pause_resume` (:90–142 — counter increments, freezes EXACTLY during the pause window, resumes after; parametrized over live `SingleThreadedAgentRuntime` vs embedded `None` runtime fixture :78–86). Naming trap: `test_group_chat.py::test_swarm_pause_and_resume` (:1500–1526) never calls `pause()` — it re-runs teams with new tasks.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "autogen", query: "pause resume group chat Team BaseGroupChat GroupChatPause GroupChatResume", limit: 20 });
```

## Verdict
Adopt out-of-band marker RPCs with cooperative agent-side flags when you need HITL freezes that preserve stream subscriptions and conversation state. Adapt the marker payloads if your host must record who requested the pause or why. Omit the manager no-op arm only if your supervisor owns in-flight turns (then it must handle them for real).
