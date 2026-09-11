<!-- capsule-v2 -->
# CoreGraphAdapter — the seam that lets one agent-loop kernel serve Lite and Supervisor without drift

**Source:** cuga-agent Apache-2.0 `main@5de53ade`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** Two agent graphs (a fast code-execution "Lite" and a delegation "Supervisor") must share one step-limit/error/playbook loop, but differ in message key, metadata key, variable manager, and model-call behaviour. How do you isolate the differences so the shared loop stays byte-identical?

## The adapter protocol
**Path/Symbol:** `src/cuga/backend/cuga_graph/nodes/cuga_agent_core/graph/graph_nodes.py` (`CoreGraphAdapter` :26-188, `append_chat_messages_with_step_limit` :191-217, `enforce_step_limit` :225-254, `inject_playbook_guidance` :257-294, `create_error_command` :297-316).
**Signature:** `class CoreGraphAdapter(ABC)` with `messages_key: str`, `metadata_key="cuga_lite_metadata"`, `execute_node_name="sandbox"`, `sender_name="CugaLite"`, abstract `get_messages(state)` + `resolve_max_steps(state, override)`, and ~14 default no-op hooks.
**Data Shape:** Defaults are exactly the legacy Lite values so the shared `ToolApprovalHandler` stays byte-identical for Lite; the Supervisor adapter overrides only `metadata_key`/`execute_node_name`/`sender_name` and the hooks it needs. `get_variable_manager` defaults to `state.variables_manager` (Lite); Supervisor overrides to `state.supervisor_variables_manager` (the phase-9 variable-coupling fix).

### Decisive source
```python
# graph_nodes.py:26-41 — defaults ARE the Lite contract; Supervisor overrides only what differs
class CoreGraphAdapter(ABC):
    messages_key: str
    metadata_key: str = "cuga_lite_metadata"
    execute_node_name: str = "sandbox"
    sender_name: str = "CugaLite"
    @abstractmethod
    def get_messages(self, state) -> List[BaseMessage]: ...
    @abstractmethod
    def resolve_max_steps(self, state, override) -> int: ...

# graph_nodes.py:139-148 — the ONE chokepoint every user-visible surface derives from
def normalize_response(self, response):
    content = strip_harmony_tokens(response.content or "")
    reasoning = (getattr(response, "additional_kwargs", None) or {}).get("reasoning_content")
    return content, reasoning
```

**Flow:** `append_chat_messages_with_step_limit(adapter, state, new, max_steps)` resolves the limit, computes `new_step_count = state.step_count + 1`, and on breach appends a canned error AIMessage and returns `(base+new+error, error)`; otherwise `(base+new, None)`. `enforce_step_limit` is the in-call_model variant that takes the already-built message list + explicit limit and returns an END error Command. `create_error_command` writes `{messages_key, script=None, final_answer, execution_complete=True, error, step_count+1}` and routes to END. `inject_playbook_guidance` appends `## Task Guidance` to the LAST HumanMessage only when a playbook policy matched and hasn't already fired, returning a NEW list (never mutates the caller's).
**Invariant:** Harmony protocol framing is stripped in `normalize_response` — the single point every user-visible surface (delivered answer, `state.messages`, streamed event, chat copy, trajectory step) derives from. Sanitizing per surface leaks; a new surface is a new leak. `reasoning` is left raw so call_model can still tell framing from a real answer when visible content is empty.
**Probe:** `tests/graph/test_shared_call_model.py` uses a `_MinimalTestAdapter` (no-op hooks = Supervisor-equivalent) to pin only the shared logic; `tests/graph/test_supervisor_feature_parity.py` asserts `_SUPERVISOR_LOOP_ADAPTER.get_variable_manager` returns `state.supervisor_variables_manager` (the phase-9 pin).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "CoreGraphAdapter messages_key resolve_max_steps normalize_response strip_harmony_tokens", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the adapter-protocol pattern: put every graph-specific difference behind an ABC with Lite-compatible defaults, keep the loop logic and error text shared and behavior-identical, and strip protocol framing at one normalize chokepoint. Adapt the hook set to your graph's actual differences (few-shot, PI injection, bind-tools, auto-continue). Omit the harmony-token vocabulary unless you carry a similar agent-protocol framing layer.
