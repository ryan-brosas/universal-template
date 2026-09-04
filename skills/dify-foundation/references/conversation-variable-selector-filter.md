<!-- capsule-v2 -->
# conversation-variable-selector-filter — How does the app layer persist only the variable scope it owns?

**Source:** dify Apache-2.0 `main@8bdf702f`; Codebase Memory `ext-dify`. **Question:** How can a generic engine event stream carry app-specific persistence without leaking storage concerns into the engine?

## Selector-prefix gate + conversation-id presence check before any write
**Path/Symbol:** `api/core/app/layers/conversation_variable_persist_layer.py:ConversationVariablePersistenceLayer.on_event` (:32-48); prefix constant `api/core/workflow/variable_prefixes.py:CONVERSATION_VARIABLE_NODE_ID`.
**Signature:** `on_event(event: GraphEngineEvent)` filtering exactly `NodeRunVariableUpdatedEvent`.
**Data Shape:** Event carries `variable.selector: tuple`; persisted only when `selector[0] == CONVERSATION_VARIABLE_NODE_ID` and `len(selector) >= 2`; conversation id read from the runtime state's system variables (`SystemVariableKey.CONVERSATION_ID`).

### Decisive source
```python
"""The graph package emits generic variable update events and stays unaware of
conversation identity or storage concerns. This layer lives in the application
core, listens to those generic events, and persists only the `conversation.*`
scope updates that matter to chat applications."""

def on_event(self, event: GraphEngineEvent) -> None:
    if not isinstance(event, NodeRunVariableUpdatedEvent):
        return
    selector = event.variable.selector
    if len(selector) < 2:
        logger.warning("Conversation variable selector invalid. selector=%s", selector)
        return
    conversation_id = get_system_text(self.graph_runtime_state.variable_pool, SystemVariableKey.CONVERSATION_ID)
    if conversation_id is None:
        return
    if selector[0] != CONVERSATION_VARIABLE_NODE_ID:
        return
    self._conversation_variable_updater.update(conversation_id=conversation_id, variable=event.variable)
```

**Flow:** engine emits a generic variable-updated event → layer checks type → shape gate (≥2 segments, else warn-and-drop) → conversation existence gate (non-chat runs silently skip) → namespace gate (`conversation.*` only) → updater writes the single variable.
**Invariant:** The engine NEVER knows about conversations — all identity resolution happens app-side from the variable pool; gates are ordered cheapest/most-general first and every early-return is silent except malformed selectors; one event = at most one variable write (no batch buffering), so persistence granularity matches emission granularity.
**Probe:** `grep -c 'CONVERSATION_VARIABLE_NODE_ID' core/app/layers/conversation_variable_persist_layer.py` → 2; direct tests `tests/unit_tests/core/app/layers/test_conversation_variable_persist_layer.py::test_persists_conversation_variables_from_variable_update_event`, `::test_skips_non_variable_update_events`.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-dify", query: "ConversationVariablePersistenceLayer NodeRunVariableUpdatedEvent selector conversation", limit: 10 });
```

## Verdict
Adopt the layered-gate filter for scoping generic events to app-owned namespaces. Adapt the prefix constant and id source. Omit nothing — this is the canonical thin-layer pattern for engine/app separation.
