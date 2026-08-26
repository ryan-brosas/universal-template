<!-- capsule-v2 -->
# Flat thread store + pair-scoped history — how do you keep every agent's transcript in one list yet replay only the right slice?

**Source:** agency-swarm MIT `main@4d1c35a6dd5ef038a5d15b39803459ff0b5f5578`; Codebase Memory `ext-agency-swarm`. **Question:** How is per-pair conversation isolation achieved without per-thread containers, and which two retrieval rules make the user thread and agent-to-agent threads behave differently?

## MessageStore flat list filtered by embedded metadata
**Path/Symbol:** `src/agency_swarm/utils/thread.py:MessageStore` (:11-113) + `ThreadManager.get_conversation_history` (:177-196); metadata written by `src/agency_swarm/messages/message_formatter.py:add_agency_metadata` (:200-254).
**Signature:** `get_conversation_history(agent: str, caller_agent: str | None = None) -> list[TResponseInputItem]`; `add_agency_metadata(message, agent, caller_agent=None, agent_run_id=None, parent_run_id=None, run_trace_id=None, history_protocol=None, timestamp=None)`.
**Data Shape:** every stored message carries `agent` (recipient) + `callerAgent` (sender, None = user) + `timestamp` (MICROSECOND epoch int) + `agent_run_id`/`parent_run_id`/`run_trace_id`/`history_protocol`; storage order IS semantic order — timestamps are diagnostics only and never drive ordering.

### Decisive source
```python
# THE asymmetry: user thread is GLOBAL across entry agents; agent pairs are BILATERAL
def get_conversation_history(self, agent: str, caller_agent: str | None = None):
    if caller_agent is None:
        messages = self._store.get_messages()
        return [m for m in messages if m.get("callerAgent") is None]   # shared user thread
    return self._store.get_conversation_between(agent, caller_agent)   # BOTH directions

# get_conversation_between matches either direction of the pair:
if (msg.get("agent") == agent1 and msg.get("callerAgent") == agent2) or \
   (msg.get("agent") == agent2 and msg.get("callerAgent") == agent1):
```

**Flow:** execution start stamps each incoming item via `add_agency_metadata` (preserve valid existing microsecond timestamp else generate `int(time.time()*1_000_000)`; default `type:"message"`) → saved to the flat store → runner history assembled as `existing_history + current items` then sanitized (see history-sanitization capsule) → after the run, new items get stamped again with the CURRENT agent name — which advances past handoffs (`extract_handoff_target_name`) so mid-run transfers attribute later items to the receiving agent.
**Invariant:** (1) All user-facing entry agents share ONE user thread (callerAgent None) regardless of recipient — porters who filter by recipient fragment the user conversation; (2) agent↔agent threads are strictly bilateral and include BOTH directions — filtering one direction loses the delegation context on reply; (3) duplicate IDs are PRESERVED by design (`test_thread_manager_allows_duplicate_ids_by_design`, placeholder ids not deduped) because tool-call outputs legitimately repeat ids; (4) save callbacks fire on EVERY add (and clear), while `replace_messages` bypasses saving deliberately.
**Probe:** `tests/test_agent_modules/test_thread_manager.py::test_user_thread_shared_across_agents` (:225), `test_placeholder_messages_are_not_deduped` (:142), `test_save_callback_triggered_on_add` (:275), `test_clear_persists_empty_message_store` (:286); metadata stamping pinned by `tests/test_messages_modules/test_message_formatter_history_protocol.py::test_prepare_history_for_runner_stores_responses_protocol_and_strips_runner_metadata` (:104).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-agency-swarm", query: "ThreadManager get_conversation_history callerAgent", limit: 10 });
```

## Verdict
Adopt the flat store + metadata-filtered projections and the global-user-thread/bilateral-agent-thread split; adapt field names to your schema but keep sender-None-means-user semantics; omit microsecond-timestamp preservation if your store orders externally. Probes green at HEAD.
