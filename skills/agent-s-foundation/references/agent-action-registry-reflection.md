<!-- capsule-v2 -->
# agent-action-registry-reflection — How does the worker learn its own action API without tool schemas?

**Source:** Agent-S MIT `main@bffdb59c`; Codebase Memory `ext-agent-s`. **Question:** How is the ACI class turned into the worker's prompt-documented API, and how do skipped actions and reflection enter the system prompt?

## Procedural memory assembly seam
**Path/Symbol:** `gui_agents/s3/agents/grounding.py:agent_action` (:25-27); `gui_agents/s3/memory/procedural_memory.py:PROCEDURAL_MEMORY.construct_simple_worker_procedural_memory` (:12-117); `gui_agents/s3/agents/worker.py:Worker.reset` (:63-88).
**Signature:** `agent_action(func)` sets `func.is_agent_action = True`; `construct_simple_worker_procedural_memory(agent_class, skipped_actions) -> str`.
**Data Shape:** Prompt template holds `TASK_DESCRIPTION` (replaced by the worker at turn 0, worker.py :193-197) and `CURRENT_OS` (replaced with `self.platform`, worker.py :77). Action inventory = every callable attribute of the agent CLASS carrying `is_agent_action`, rendered as `def name(signature): docstring`.

### Decisive source
```python
# grounding.py — the whole registration mechanism
def agent_action(func):
    func.is_agent_action = True
    return func

# procedural_memory.py — reflection into the class inventory
for attr_name in dir(agent_class):
    if attr_name in skipped_actions:
        continue
    attr = getattr(agent_class, attr_name)
    if callable(attr) and hasattr(attr, "is_agent_action"):
        signature = inspect.signature(attr)
        procedural_memory += f"""
    def {attr_name}{signature}:
    '''{attr.__doc__}'''"""
```

**Flow:** Worker.reset builds `skipped_actions` (`set_cell_values` on non-linux; `call_code_agent` when `grounding_agent.env` or its `.controller` is missing — worker.py :64-73) → renders prompt from the class → generator + reflection agents created → at turn 0 `TASK_DESCRIPTION` substituted and stored as messages[0] (worker.py :193-197); reflection agent gets task + initial screenshot appended to its system prompt once (:144-157).
**Invariant:** (1) The API surface IS the decorator set — adding an `@agent_action` method changes the model-facing contract automatically; non-decorated helpers stay invisible. (2) Skips are platform/capability-driven and must be computed per reset, not hardcoded. (3) The prompt demands exactly ONE call per fenced block and forbids invented methods (:104-107) — this is what makes single-action validation sound downstream. (4) Reflection output rules: Case 1 off-plan / Case 2 on-track / Case 3 complete, never suggesting a specific action (:130-142).
**Probe:** `grep -c '@agent_action' gui_agents/s3/agents/grounding.py` → 15.
**Probe:** `grep -n 'hasattr(attr, "is_agent_action")' gui_agents/s3/memory/procedural_memory.py` → :79 (the sole `is_agent_action` occurrence in that file; the decorator lives in grounding.py :26).
**Probe:** `tests/test_providers.py` exercises the same LMMAgent construction path these agents use.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-agent-s", query: "construct_simple_worker_procedural_memory agent_action", limit: 5 });
```

## Verdict
Adopt decorator-marked methods + introspected signatures as a self-documenting action registry (no tool-schema plumbing), and the capability-based skip list; adapt the prompt text and OS placeholders to your environment grammar; omit OSWorld-specific sudo-password guidance embedded in the prompt.
