<!-- capsule-v2 -->
# Subgraph event projection — how do you turn raw LangGraph `(namespace, state_delta)` updates into UI events without leaking internal state?

**Source:** cuga-agent Apache-2.0 `main@5de53ade77c36166da6ace906af488b2b445454f`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** With `astream(stream_mode="updates", subgraphs=True)`, how does a node's state delta become one named frontend event, and which events must be suppressed entirely?

## AgentLoop.get_event_message
**Path/Symbol:** `src/cuga/backend/cuga_graph/utils/agent_loop.py:361-536` (`get_event_message`; consumers `_spawn_to_stream_event` :270-313, `get_output` policy envelope :638-725).
**Signature:** `get_event_message(self, event) -> StreamEvent` where event is either `(namespace_tuple, {node_name: state_dict})` (subgraphs=True) or `{node_name: state_dict}`.
**Data Shape:** output `StreamEvent(name, data)`; empty-name or empty-data sentinels (`StreamEvent("", "")`) mean "skip" — the run loop drops them before formatting.

### Decisive source
```python
# subgraph call_model branch (:387-415): code vs text projection
if "script" in state_data and state_data["script"] and state_data["script"].strip():
    return StreamEvent(name="CodeAgent", data=json.dumps({...,"code": state_data["script"],...}))
else:
    # Text/reasoning output - only when last chat turn is a non-empty assistant message
    ...
    if content and content.strip():
        return StreamEvent(name="CodeAgent_Reasoning", data=content)
    return StreamEvent(name="", data="")   # Skip empty events

# root-level routing commands (:472-475)
if event[first_key] is None:
    logger.debug(f"Skipping event with None state for node: {first_key}")
    return StreamEvent(name=str(first_key), data="")

# unified policy event (:492-509) — detected by metadata flags, NOT node name
metadata = event_data.get("cuga_lite_metadata", {})
if metadata.get("policy_blocked") or metadata.get("policy_matched"):
    policy_event = {"type": "policy", ..., "content": event_data.get("final_answer", ""), ...}
    return StreamEvent(name="Policy", data=json.dumps(policy_event))
```

**Flow:** tuple → read node name from the FIRST key of the state delta → subgraph namespace: project `call_model` to CodeAgent/CodeAgent_Reasoning, project `sandbox` to execution-output CodeAgent (scanning messages in REVERSE for the `"Execution output:"` marker), other nodes pass name-only → root level: None-delta (routing Command) skipped, subgraph-completion keys (`CugaLiteSubgraph`/`CugaLiteCallback`, duck-typed via missing `input`/`url` fields) render final_answer-or-last-message as CodeAgent, full `AgentState` nodes get per-node projections (BrowserPlanner→previous_steps JSON, ActionAgent→tool_calls).
**Invariant:** (1) an update carrying NO new information must yield a skip-sentinel, never a blank flash on the UI; (2) policy events are keyed off `cuga_lite_metadata.policy_blocked|policy_matched` wherever they appear — not off node identity; (3) the same policy envelope shape is re-emitted at terminal-answer time in `get_output` (:716-725), with markdown bodies per policy type (✋ approval w/ tools list + code preview fence, 🛑 blocked w/ custom response, 📖 playbook, 🔧 tool guide) — and appworld benchmarks are excluded from wrapping.
**Probe:** no direct unit test for get_event_message (coverage caveat — it's the display layer); pinned indirectly end-to-end by `tests/integration/a2a/conftest.py` + the policy e2e suites under `src/cuga/backend/cuga_graph/policy/tests/`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "get_event_message cuga_lite_metadata policy_blocked subgraphs", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the skip-sentinel discipline and metadata-keyed (not node-keyed) policy detection; adopt the reverse-scan marker extraction for execution output when your protocol embeds outputs in message history; adapt node-name→event-name mapping to your graph; omit browser-era per-node branches if you have no browser planner. Coverage caveat: source-read verified, integration-covered, no dedicated unit test.
