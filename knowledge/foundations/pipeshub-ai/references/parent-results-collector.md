<!-- capsule-v2 -->
# collect_parent_tool_results (last-REAL-user-message boundary)

## Source
pipeshub-ai Apache-2.0 `main@4a02110d`; Codebase Memory `pipeshub-ai`. **Question:** Which of the calling agent's tool results belong in a child's handoff digest — and why do injected user messages not count as boundaries?

## Path/Symbol
`tools/builtin/coordination/parent_results.py` — `ParentToolResult` frozen dataclass (:52–57), `collect_parent_tool_results(messages, exclude_tool_names=DEFAULT_EXCLUDED)` (:63–104). Excludes `{run_code, install_packages, read_sandbox_file}` by default (:43–45).

## Signature
Boundary scan: last `UserMessage` with `injected=False`; everything AFTER it is the current leg. Tool names recovered via `tool_name_by_call_id[call.id] = call.name` from AssistantMessage.tool_calls (ToolMessages carry only tool_call_id); unmatched ids → `"unknown_tool"`; error/empty results skipped.

## Data Shape
Returns `[ParentToolResult(tool_name: str, content: str)]` in conversation order. Input must be the parent's fresh post-response snapshot (`RouteContext.messages` / ToolScope.messages) — the same snapshot every special-route handler already receives.

### Decisive source
```python
Programmatically injected `UserMessage`s (recovery nudges from the
completion gate, truncation recovery, loop-strategy phase transitions)
are explicitly excluded from the boundary search: they are system
directives, not new user requests, and treating them as boundaries
would hide all tool results gathered before the nudge from a child
agent that needs them (e.g. `coding_agent` losing the parent's Jira
data after a completion-gate nudge forced a file-generation retry).
```

**Flow:** AgentTool.handle() calls this over ctx.messages → merges dependency results FIRST → digest + JSON file staged into child. Sandbox tools excluded by default (their stdout is environment noise, not data).

**Invariant:** `msg.injected is False` on the boundary check is the whole point: recovery nudges LOOK like new turns but aren't — treating them as boundaries orphans every result gathered before them. No real user message at all ⇒ fall back to whole list (sub-agent conversations have no user turn).

**Probe:** `tests/unit/agent_loop_lib/tools/builtin/coordination/test_parent_results.py` — pairing :31, stale-leg exclusion :40, **injected-no-boundary :55** (regression for the completion-gate bug), errors excluded :75, sandbox excluded :83, empty skip :95, no-user fallback :103, unknown_tool :112.

## Get live surrounding code
**Retrieve:**
```bash
codebase-memory-mcp cli search_graph --project pipeshub-ai --semantic-query '["collect_parent_tool_results","ParentToolResult","injected"]'
```

## Verdict
Adopt the last-real-user boundary + call-id→name re-association + default sandbox-tool exclusions; adapt the injected flag to host's message model (the invariant survives any naming).
