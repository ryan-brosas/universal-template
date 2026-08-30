<!-- capsule-v2 -->
# Shared call_model — the routing ladder that turns a model response into a Command (execute / END / auto-continue)

**Source:** cuga-agent Apache-2.0 `main@5de53ade`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** Both agent graphs need one `call_model` node that assembles the system+few-shot+conversation message list, injects PI/playbook/variables, enforces the step and tool budgets, and routes code→execute, text→END, interim→auto-continue — with the per-graph differences delegated to the adapter. What are the non-obvious invariants a porter would get wrong?

## The factory
**Path/Symbol:** `src/cuga/backend/cuga_graph/nodes/cuga_agent_core/graph/shared_nodes.py` (`create_call_model_node` :55-349, `TOOL_BUDGET_EXHAUSTED_INSTRUCTION` :47-52).
**Signature:** `create_call_model_node(adapter, base_model, settings) -> Callable` returning `async def call_model(state, config) -> Command`.
**Data Shape:** `active_model = configurable.get("llm") or base_model` (runtime override); `base_prompt = state.prepared_prompt`; system content augmented by `adapter.prepare_system_content`; variables summary appended as an outbound-only addendum; messages_for_model = `[system] + few-shot + conversation`.

### Decisive source
```python
# shared_nodes.py:171-184 — variables addendum is rebuilt every turn and must stay OUT of persisted history (#600)
# Persisting it left every message that was once `is_last` holding its own copy, growing context ~5x faster
# than the conversation and tripping the provider's context limit mid-task. Unlike `pi` and `playbook_guidance`
# (guarded to fire once), this one has no guard, so it is the only addendum that accumulates.
outbound_content = content
if variables_summary_text and is_last:
    outbound_content = content + variables_addendum

# shared_nodes.py:201-213 — budget exhausted = ONE grace turn with tools withheld
budget_exhausted = bool(getattr(state, "tool_budget_exhausted", False))
if budget_exhausted:
    messages_for_model.append({"role": "user", "content": TOOL_BUDGET_EXHAUSTED_INSTRUCTION})
# ...then bound = active_model (no bind-tools), step-limit exempted, code forced to None, auto-continue disabled
```

**Flow:** sync langfuse callbacks → tool-approval resumption check (priority) → resolve model → build system content → context summarization (`apply_context_summarization`) → assemble messages (PI injected into the single human message when `len==1` and no `## User Context`; playbook guidance into the last human; variables addendum outbound-only) → budget-exhausted grace turn → resolve bound model (Lite binds tools) → `adapter.ainvoke_model` → `normalize_response` → `extract_code_from_model_response` → step-limit guard (exempt when budget exhausted) → tool-approval interrupt for generated code → route: `code → execute_node_name`; text → `classify_auto_continue` (Lite only) → `goto="call_model"` with a `HumanMessage("continue")`; else END with `final_answer`.
**Invariant:** (1) The variables addendum and budget-exhausted instruction are OUTBOUND-ONLY — never persisted, so they can't accumulate in history. (2) A spent budget gets one final synthesis pass with an empty tool list (a constraint, not a request) then END — otherwise every tool call raises and the model burns LLM calls until the step limit trips into an error. (3) Reasoning-only models finalize with empty visible content: fall back to `reasoning` as the answer, but never surface raw harmony framing. (4) If even that is empty, recover the last `Execution output:` body from a HumanMessage.
**Probe:** `tests/graph/test_shared_call_model.py` pins the 5 routing branches (code→execute, text→END, step-limit→END error, auto-continue→"continue", approval-resumption priority); `tests/graph/test_call_model_budget_exhausted.py` pins the grace-turn behaviour.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "create_call_model_node tool_budget_exhausted classify_auto_continue final_answer reasoning", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the outbound-only addendum discipline, the grace-turn budget-exhaustion path, the reasoning fallback with harmony-token guard, and the adapter-delegated routing ladder. Adapt the summarization trigger and budget caps to your provider. Omit the Langfuse callback sync and Lite-specific bind-tools unless you need them.
