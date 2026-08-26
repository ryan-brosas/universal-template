<!-- capsule-v2 -->
# Team state checkpointing — how do you snapshot a whole team so state survives re-registration and different runtimes?

**Source:** autogen (MIT — LICENSE-CODE) `main@027ecf0a379bcc1d09956d46d12d44a3ad9cee14`; Codebase Memory project `autogen` (FULL, 16,432 nodes / 86,358 edges, generation 2026-08-24T16:12:29Z). **Question:** What should the checkpoint be keyed by, who performs the save/load, and what must be refused mid-run?

## Name-keyed agent_states delegated through runtime state methods
**Path/Symbol:** `python/packages/autogen-agentchat/src/autogen_agentchat/teams/_group_chat/_base_group_chat.py` `save_state` :748–796, `load_state` :798–834; `python/packages/autogen-agentchat/src/autogen_agentchat/state/_states.py` `TeamState` :20–24; `python/packages/autogen-core/src/autogen_core/_single_threaded_agent_runtime.py` `agent_save_state`/:880–881, `agent_load_state`/:883–884.
**Signature:** `async def save_state(self) -> Mapping[str, Any]` · `async def load_state(self, state: Mapping[str, Any]) -> None` · shape `{"agent_states": {<participant-or-manager NAME>: state}}`.
**Data Shape:** `TeamState(BaseState)` pydantic: `agent_states: Mapping[str, Any]` (+`type`/`version`); manager states extend `BaseGroupChatManagerState` (`message_thread`, `current_turn`) with per-policy fields (`next_speaker_index` / `previous_speaker` / `current_speaker`).

### Decisive source
```python
# NOTE: we don't use the agent ID as the key here because we need to be able to decouple
# the state of the agents from their identities in the agent runtime.
agent_states: Dict[str, Mapping[str, Any]] = {}
for name, agent_type in zip(self._participant_names, self._participant_topic_types, strict=True):
    agent_id = AgentId(type=agent_type, key=self._team_id)
    agent_states[name] = await self._runtime.agent_save_state(agent_id)
```
```python
if self._is_running:
    raise RuntimeError("The team cannot be loaded while it is running.")
self._is_running = True
try:
    team_state = TeamState.model_validate(state)
    for name, agent_type in zip(self._participant_names, self._participant_topic_types, strict=True):
        if name not in team_state.agent_states:
            raise ValueError(f"Agent state for {name} not found in the saved state.")
        await self._runtime.agent_load_state(agent_id, team_state.agent_states[name])
    ...
except ValidationError as e:
    raise ValueError("Invalid state format. The expected state format has changed since v0.4.9. ...") from e
finally:
    self._is_running = False
```
```python
# runtime side is deliberately thin — loading LAZILY INSTANTIATES through the factory:
async def agent_save_state(self, agent: AgentId) -> Mapping[str, Any]:
    return await (await self._get_agent(agent)).save_state()
```

**Flow:** ensure `_init` → save: zip(names, topic_types, strict) → `runtime.agent_save_state(AgentId(type=topic_type, key=team_id))` per participant + manager → name-keyed dict · load: refuse if running → set mutex → validate `TeamState` → missing name ⇒ `ValueError` → delegate per name → clear mutex in `finally`.
**Invariant:** keys are participant NAMES, never AgentIds — this is what lets a checkpoint move between team instances and runtimes (v0.4.9 format note); loading must not race a live run (`_is_running` mutex, cleared in finally); runtime delegation instantiates agents lazily, so load works before any message was ever routed.
**Probe:** `python/packages/autogen-agentchat/tests/test_group_chat.py::test_round_robin_group_chat_state` (:521–564 — team2 loads team1's state: equal saved dicts, identical per-agent model contexts, manager `_current_turn`/`_message_thread` equal across teams).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "autogen", name_pattern: "^save_state$|^load_state$", file_pattern: "*agentchat/src*", limit: 25 });
```

## Verdict
Adopt name-keyed checkpoint maps plus a refuse-while-running mutex for any long-lived multi-agent session. Adapt the state schemas (here pydantic BaseState algebra with versioned `type` discriminators). Omit the v0.4.9 migration ValueError text and the pydantic Component save/load layer if your host serializes differently.