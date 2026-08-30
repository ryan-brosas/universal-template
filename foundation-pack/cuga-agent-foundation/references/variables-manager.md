<!-- capsule-v2 -->
# Variables manager — how do sandbox variables persist through checkpoints and bridge across agents?

**Source:** cuga-agent Apache-2.0 `main@5de53ade77c36166da6ace906af488b2b445454f`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** How is a rich in-memory key-value store made LangGraph-checkpointable without changing its API, and how are its values handed to sub-agents?

## Two managers, one API: live-object vs state-backed
**Path/Symbol:** `src/cuga/backend/cuga_graph/state/agent_state.py:VariablesManager` (:112-809) and `StateVariablesManager` (:812-938); consumer bridge `nodes/cuga_agent_core/execution/variable_bridge.py:VariableBridge`.
**Signature:** `VariablesManager.add_variable(value, name=None, description=None) -> str`; auto-names `variable_{counter}`; `StateVariablesManager(state: 'AgentState')` overrides `variables` / `variable_counter` / `_creation_order` as properties over `state.variables_storage` (dict-of-dicts), `state.variable_counter_state`, `state.variable_creation_order`.
**Data Shape:** Stored entry = `{value, description, type, created_at: ISO-str, count_items}`. `type`/`count_items` derived via `VariableMetadata._type_and_count`, which recognizes VariableUtils set-tags (`{"__set_type__": ...}` tagged dicts) before falling back to python type names. Values pass through `VariableUtils.sanitize_value` on write and `hydrate_value` on read.

### Decisive source
```python
# agent_state.py:820-832 — property override turns live objects into checkpointable dicts
@property
def variables(self) -> Dict[str, VariableMetadata]:
    """Get variables dict, reconstructing VariableMetadata objects from stored dicts."""
    result = {}
    for name, meta_dict in self.state.variables_storage.items():
        result[name] = VariableMetadata(
            value=meta_dict['value'],
            description=meta_dict.get('description', ''),
            created_at=datetime.fromisoformat(meta_dict['created_at'])
            if isinstance(meta_dict.get('created_at'), str)
            else meta_dict.get('created_at'),
        )
    return result

# :892-900 — creation order is LRU-by-update: re-adding moves to end
if name in self.state.variable_creation_order:
    self.state.variable_creation_order.remove(name)
    self.state.variable_creation_order.append(name)
else:
    self.state.variable_creation_order.append(name)

# :875-878 — explicit names advance the counter so auto-names never collide
if name.startswith("variable_") and name[9:].isdigit():
    num = int(name[9:])
    if num >= self.variable_counter:
        self.variable_counter = num
```

**Flow:** sandbox code calls add/get → base class mutates in-memory maps; State subclass writes the same logical fields straight into AgentState so every mutation rides normal LangGraph checkpointing → summaries/previews render LRU-ordered (`get_last_n_variable_names`) → after a delegated sub-agent run, `VariableBridge.extract_values(variables_storage)` strips metadata to `{name: raw_value}`, skipping entries lacking a `value` key, and copies them into the caller's manager.
**Invariant:** All mutations MUST go through the same field names on both classes — the subclass changes STORAGE, not semantics; counter advancement on explicit `variable_N` names prevents silent overwrite collisions after partial resets (`reset_keep_last_n` recomputes the max kept N). Creation order is update-order (LRU), not insert-only. Preview helpers truncate recursively with depth/item/char budgets and never raise.
**Probe:** `nodes/cuga_agent_core/tests/execution/test_variable_bridge.py::test_extract_values_returns_name_value_dict` + `test_extract_values_skips_entries_without_value_key` + empty-storage test (pins the {name: value} contract and malformed-entry skip). Round-trip persistence pinned by e2e graph tests using real checkpointer (`test_tool_call_budget_e2e.py` pattern).
**Why a porter gets this wrong:** copying only `VariablesManager` gives an API that compiles but loses everything at the first checkpoint boundary; copying only the dict shape loses LRU order and the set-tag typing that summaries rely on.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "StateVariablesManager.add_variable", limit: 3 });
// → agent_state.py 865-902; base 172-238
```

## Verdict
Adopt the dual-manager split (live class + property-backed state subclass), sanitize/hydrate at the boundaries, LRU `_creation_order`, counter-advancing explicit names, and the extract-values bridge for delegation. Adapt naming/storage to your state container. Omit markdown logging (`tracker_enabled` diagnostics).
