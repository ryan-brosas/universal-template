<!-- capsule-v2 -->
# Config Wiring — how does the policy system reach every graph node (including subgraphs) without constructor plumbing?

**Source:** cuga-agent Apache-2.0 `main@5de53ade`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** How do you give deep LangGraph nodes — including compiled subgraph nodes — access to one shared policy system without threading it through every constructor?

## Singleton + configurable injection
**Path/Symbol:** `src/cuga/backend/cuga_graph/policy/configurable.py` (`PolicyConfigurable.get_instance` :63-68, `from_config` :70-90, `initialize` :92-202, `create_context_from_state` :251-350); injection at `src/cuga/backend/cuga_graph/graph.py:130-147` and `:262-266`.

**Signature:** `PolicyConfigurable.from_config(config: RunnableConfig) -> PolicyConfigurable`; `get_config_with_policy(self, base_config: dict = None) -> dict` sets `config["configurable"]["policy_system"] = self`.

**Data Shape:** The object bundles `storage` (PolicyStorage w/ embeddings), `agent` (PolicyAgent), `llm` (chat model for NL conflict resolution), `embedding_function`. `_initialized` is a class attribute on the singleton; `initialize()` resolves DB path relative to `DBS_DIR` when not absolute and falls back to `settings.policy.*` / `get_embedding_config()`.

### Decisive source
```python
# configurable.py:81-90 — explicit instance wins, singleton otherwise.
config = ensure_config(config)
configurable = config.get("configurable", {})
policy_system = configurable.get("policy_system")
if policy_system and isinstance(policy_system, cls):
    return policy_system
return cls.get_instance()
```
And why subgraphs need no plumbing (`graph.py:263-266`, comment verified at HEAD):
> "The policy_system is NOT passed here because it's accessed at runtime via config["configurable"]["policy_system"]. When the main graph invokes this subgraph node, LangGraph automatically passes the config down to the subgraph's nodes."

**Flow:** build_graph compiles with `checkpointer=MemorySaver()` → each invoke carries `configurable.policy_system` → any node calls `from_config(config)` → lazy `await initialize()` on first match if needed.

**Invariant:** Context extraction must never treat tool-execution output as user intent: `create_context_from_state` (:288-297) walks `chat_messages` in reverse to find the last HumanMessage that does NOT contain "Execution output" / "Execution output preview" / "Error during execution" — otherwise formatter policies would re-match their own injected text on the next turn. For output targets it prioritizes `state.final_answer` before the last message content (:319-325).

**Probe:** `src/cuga/backend/cuga_graph/policy/tests/helpers.py` builds test policy systems via this exact wiring; e2e suites (`test_e2e_intent_guard.py`, `test_e2e_output_formatter.py`) run full graphs where nodes receive the system only through `configurable` — no direct construction. Caveat: no unit test pins `from_config`'s fallback branch alone; it's covered only transitively by e2e runs.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "PolicyConfigurable from_config singleton", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt ride-along config injection + singleton fallback for anything a whole agent graph needs (policies, feature flags, per-run registries). Adapt storage/embedding backend selection. Omit the demo CRM/email/filesystem default supervisor agents (`graph.py:318-383`) — those are product demo fixtures.
