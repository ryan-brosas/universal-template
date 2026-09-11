<!-- capsule-v2 -->
# Unknown-tool retry message — which tools belong in "available tools" when the model hallucinates a name?

**Source:** pydantic-ai Apache-2.0 @ `fde1bbb6aff461769a1d6d2440c33c232bf90f03`; Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** How should the retry prompt enumerate tools without advertising ones the model cannot see yet?

## unknown-tool-retry-message
**Path/Symbol:** `pydantic_ai_slim/pydantic_ai/tool_manager.py::ToolManager._check_unknown_tool_name` region (:501–514).
**Signature:** `available = sorted(n for n, t in self.tools.items() if self.ctx.is_tool_available(t.tool_def))` then three-way message fork.
**Data Shape:** `self.tools` = ALL registered tools (superset); visibility gate = same `ctx.is_tool_available` used by the unavailable-tool check.

### Decisive source
```python
# Name only what the model can call this turn, the same `is_tool_available` gate the
# unavailable-tool check applies, so a name that tool search or `load_capability` has yet
# to reveal stays out of this message.
available = sorted(n for n, t in self.tools.items() if self.ctx.is_tool_available(t.tool_def))
if available:
    msg = f'Available tools: {", ".join(f"{n!r}" for n in available)}'
elif self.tools:
    msg = 'No tools are available yet: search for the tools you need.'
else:
    msg = 'No tools available.'
raise ModelRetry(f'Unknown tool name: {name!r}. {msg}')
```

**Flow:** model calls a nonexistent/unrevealed tool → manager filters registrations through the visibility gate → non-empty: sorted name list; empty-but-registered: hint that SEARCH reveals tools; truly zero: bare statement → ModelRetry returns to the model instead of aborting.
**Invariant:** three rules:
1. The enumeration gate must be THE SAME predicate that hides tools (tool-search deferral, capability loading) — listing registered-but-hidden tools teaches the model names whose schemas it never received, producing calls that fail again.
2. The middle branch is new UX for deferred-toolset flows: "No tools are available yet" converts a dead end into the correct next action (search).
3. Retry-not-abort: unknown tool names are recoverable model errors; the fix is information, not termination (#7572 "Only list available tools in the unknown-tool retry message").
**Probe:** `tests/test_tool_availability.py` (`No tools are available yet` pinned) + `tests/test_agent.py` unknown-tool suites.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pydantic-ai", query: "unknown tool name available tools is_tool_available ModelRetry ToolManager", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt gate-consistent enumeration + the search-hint middle branch in any tool-routing loop with deferred discovery; adapt wording; omit the middle branch where all tools are always visible.
