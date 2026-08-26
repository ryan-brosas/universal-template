<!-- capsule-v2 -->
# AgentState — which state keys and reducers must survive LangGraph checkpoint round-trips?

**Source:** cuga-agent Apache-2.0 `main@5de53ade77c36166da6ace906af488b2b445454f`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** What does the shared state schema look like, and which fields carry cross-turn invariants that a naive port silently breaks?

## AgentState: the single pydantic state for the whole graph
**Path/Symbol:** `src/cuga/backend/cuga_graph/state/agent_state.py:AgentState` (:964-1054), `keep_highest` reducer (:29-40), `StateVariablesManager` (:812-938).
**Signature:** `class AgentState(BaseModel)` — plain fields (no per-field Annotated reducers except `tool_calls_used_thread`); `def keep_highest(current: Optional[int], incoming: Optional[int]) -> int`; `AgentState.variables_manager -> StateVariablesManager` property.
**Data Shape:** ~50 fields; policy-relevant ones: `cuga_lite_metadata: Dict[str,Any]` (policy decision ledger rides here — see observability capsule), `hitl_action/hitl_response` (approval interrupt/resume payload), `sender`, `env_policy: List[dict]`, `sources`, plus three message lists (`chat_messages`, `chat_agent_messages`, `supervisor_chat_messages`) that sliding-window/summarization trim. Variables persist as `variables_storage: Dict[str, Dict]` + `variable_counter_state: int` + `variable_creation_order: List[str]`.

### Decisive source
```python
# :29-40 — a counter that can only ever go up; builtins can't be reducers
def keep_highest(current: Optional[int], incoming: Optional[int]) -> int:
    """LangGraph reducer: a counter that can only ever go up.

    Used for ``tool_calls_used_thread``. Builtin ``max`` cannot be used directly —
    LangGraph inspects the reducer's signature and builtins have none.

    Monotonicity is what makes the conversation ceiling hold regardless of caller:
    the server rebuilds state from the checkpoint on every turn, so the incoming
    value is sometimes the field's default 0, which would otherwise silently reset
    the ceiling mid-conversation.
    """
    return max(current or 0, incoming or 0)

# :969-976 — why it lives on the PARENT state, not the subgraph
# tool_calls_used_thread has to live on the PARENT state because CugaLite/CugaSupervisor
# run as subgraphs: a subgraph is re-entered fresh on every turn and only shares state
# keys the parent also declares... The ``max`` reducer makes it monotonic, so a caller
# that rebuilds state and passes the default 0 cannot silently reset the ceiling.
tool_calls_used_thread: Annotated[int, keep_highest] = 0
```

**Flow:** server rebuilds state each turn (incoming counter often 0) → node returns update `{tool_calls_used_thread: n}` → reducer takes max against checkpointed value → parent passes the key into subgraphs, which share only co-declared keys → budget checks read the monotonic value; exhaustion ends the turn with a synthesized answer instead of looping.
**Invariant:** A conversation-wide counter MUST be (a) declared on the parent state so subgraph re-entry doesn't reset it, and (b) reduced with keep-highest so a default-0 rebuild can't rewind it. Plain int fields get last-write-wins semantics in LangGraph — do not copy this field without its Annotated reducer. Custom wrapper function required: LangGraph inspects reducer signatures and rejects builtins.
**Variables-manager duality:** `VariablesManager` keeps live `VariableMetadata` objects; `StateVariablesManager` subclasses it and overrides `variables`/`variable_counter`/`_creation_order` as PROPERTIES backed by `state.variables_storage` dicts (`created_at` ISO round-trip) — same API surface, checkpointable storage. Malformed entries without a `value` key are skipped by consumers (VariableBridge.extract_values).
**Probe:** `src/cuga/backend/cuga_graph/nodes/cuga_lite/executors/tests/test_tool_call_budget_delegation.py::test_keep_highest_ignores_a_default_zero` (:212-220) asserts `keep_highest(100,0)==100` etc.; `nodes/cuga_lite/tests/test_tool_call_budget_e2e.py` runs the REAL graph + MemorySaver across two turns asserting `turn1["tool_calls_used_thread"]==3` survives the checkpoint and accumulates to `==5` (:131,:147).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "keep_highest", limit: 5 });
// → agent_state.py Function 29-40 + direct reducer test
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "StateVariablesManager.add_variable", limit: 3 });
// → agent_state.py 865-902 vs VariablesManager.add_variable 172-238
```

## Verdict
Adopt the parent-state + monotonic-reducer placement rule for any cross-turn budget/counter, the custom-function-not-builtin reducer requirement, and the property-backed subclass trick to make a rich manager checkpoint-safe. Adapt field names and the message-list trio to your host. Omit browser/API planner fields you don't carry.
