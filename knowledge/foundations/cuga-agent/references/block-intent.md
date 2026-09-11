<!-- capsule-v2 -->
# Block Intent — the exact state a graph must produce when a guard rejects the user's request

**Source:** cuga-agent Apache-2.0 `main@5de53ade`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** When an IntentGuard matches, what minimal set of state updates makes every downstream consumer (UI, loop controller, checkpoint) agree the run is over?

## END command with five coordinated updates
**Path/Symbol:** `src/cuga/backend/cuga_graph/policy/enactment.py:332-383` (`PolicyEnactment._enact_block_intent`); consumed at `nodes/cuga_lite/adapter/prepare_node.py:139-150`.

**Signature:** `_enact_block_intent(state, policy_match, adapter=None, metadata_key=None) -> tuple[Command, None]`.

**Data Shape:** `Command(goto=END, update={...})` — update carries the messages list, `final_answer`, `execution_complete`, metadata under the resolved key, and `step_count`. `allow_override=True` guards never reach here (matcher maps them to LOG_ONLY at `agent.py:391-394`).

### Decisive source
```python
# enactment.py:354-383 — adapter seam + full payload
if adapter is not None:
    base_messages = adapter.get_messages(state)
    messages_key = adapter.messages_key
    resolved_metadata_key = metadata_key or adapter.metadata_key
else:
    base_messages = state.chat_messages      # legacy literals preserved
    messages_key = "chat_messages"
    resolved_metadata_key = metadata_key or "cuga_lite_metadata"

return (Command(
    goto=END,
    update={
        messages_key: base_messages + [blocked_message],   # AIMessage(action.content)
        "final_answer": policy_match.action.content,
        "execution_complete": True,
        resolved_metadata_key: {
            "policy_blocked": True,
            "policy_id": ..., "policy_name": ...,
            "policy_type": "intent_guard",
            "policy_reasoning": ..., "policy_confidence": ...,
            "response_content": policy_match.action.content,
        },
        "step_count": 0,
    },
), None)
```

**Flow:** matcher returns IntentGuard match with BLOCK_INTENT → enactment wraps in Command → calling node (`prepare_tools_and_apps`) sees `command` is not None and returns it immediately — before tools are fetched or any LLM runs — so the blocked response becomes the run's final answer.

**Invariant:** All five keys move together. Omit `final_answer` and the UI shows nothing; omit `execution_complete=True` and the step loop keeps running; omit `step_count=0` and resumable threads inherit stale counters; omit the metadata payload and the UI can't render *why* the run was blocked. The adapter-vs-legacy branch exists so Lite (`cuga_lite_metadata`) and Supervisor (`supervisor_metadata`) share one implementation without leaking each other's key names.

**Probe:** `src/cuga/backend/cuga_graph/policy/tests/test_e2e_intent_guard_priority.py:161 assert metadata.get('policy_blocked')` and `:168 assert 'not allowed' in final_answer.lower() or 'blocked' ...` — full-graph proof that blocking produces both the marker metadata and the user-visible answer; `test_e2e_intent_guard.py` covers the basic block path.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "_enact_block_intent BLOCK_INTENT END command", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the atomic five-key block payload and the adapter-parameterized message/metadata key resolution. Adapt key names to your state schema. Omit the legacy-literal fallback once your only callers pass adapters.
