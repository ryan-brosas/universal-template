<!-- capsule-v2 -->
# Availability refusal messaging — how does an unavailable tool become a corrective retry prompt instead of a dead end?

**Source:** pydantic-ai MIT `main@b3cdbc96796f0294f1ac6943cdba70d14af8a0ef`; Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai` (full mode, coverage clean). **Question:** When the model calls a tool that exists but isn't available yet (deferred-loading / capability-gated), what message does it get and why is the budget treatment different from unknown tools?

## _ToolUnavailable + _unavailable_reason
**Path/Symbol:** `pydantic_ai_slim/pydantic_ai/tool_manager.py:_ToolUnavailable` (97–111), `ToolManager._unavailable_reason` (514–545), `_resolve_tool` (496–512).
**Signature:** `_unavailable_reason(tool_def: ToolDefinition) -> str | None`; refusal raised as `_ToolUnavailable(message, tool)` (a `ModelRetry` subclass carrying its tool).
**Data Shape:** Two distinct refusals: unknown name (`ModelRetry('Unknown tool name: ... Available tools: ...')`) vs. not-available-yet (`_ToolUnavailable`). The unavailable variant carries `tool` because it's raised during resolution — before the caller has bound the resolved tool — and its retry budget must be the TOOL's own `max_retries`, not the manager default.

### Decisive source
```python
# tool_manager.py:514-545 — the message is written to be ACTED ON
def _unavailable_reason(self, tool_def):
    if self.ctx.is_tool_available(tool_def):
        return None
    # `is_tool_available` makes the decision, so introspection and execution cannot disagree;
    # the rest only picks which way to point the model.
    if (capability_id := tool_def.capability_id) is not None and (
        capability_id not in self.ctx.available_capability_ids
    ):
        return (f'Tool {tool_def.name!r} is not available yet: it belongs to capability '
                f'{capability_id!r}. Call `load_capability` for it first, then call the tool again '
                "once you've read the capability's instructions.")
    return (f'Tool {tool_def.name!r} is not available yet: search for it first, then call it again '
            "once you've seen its schema.")
```

**Flow:** Model calls a search-gated or capability-owned tool → resolution finds it in the dict but `is_tool_available(tool_def)` says not yet → `_ToolUnavailable` raised with a directive naming the exact next action (`load_capability` vs. `search`) → validation failure path gives the FIRST such refusal per tool a free pass (`availability_refused`, run-scoped) → later uncorrected refusals charge normally so a disobedient model still terminates.
**Invariant:** "Not available YET" wording (never "unknown") keeps the model searching/loading instead of concluding the tool doesn't exist; the resulting search/load exchange restores the history that justifies the call, keeping compacted histories coherent. The availability decision lives in ONE place (`is_tool_available`) so introspection (what's shown to the model) and execution can't disagree. Capability-owned tools get the load instruction because searching can't help until their capability is active.
**Probe:** `tests/test_tool_availability.py` pins availability gating end-to-end; `tests/test_tool_availability_portability.py` covers cross-provider replay of availability parts.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pydantic-ai", query: "_ToolUnavailable _unavailable_reason is_tool_available availability_refused", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the two-tier refusal taxonomy + action-naming messages + one-free-refusal budget carve-out; adapt what "availability" means in your host (feature flags, deferred loading); omit capability-id specifics if you have no capability bundles. Caveat: none — read at HEAD this session; test files located but only probed via grep + targeted reads.
