<!-- capsule-v2 -->
# ToolFailure declarative failure protocol — run-but-failed tools with policy ladder

**Source:** crewAI MIT `main@9e9a8577`; Codebase Memory `ext-crewAI`. **Question:** How can a tool report "the call worked but the action failed" (HTTP 200 with ok:false, MCP isError) without string-sniffing — and how does the agent react?

## Connected graph-selected seam
**Path/Symbol:** `lib/crewai/src/crewai/tools/tool_failure.py` — `ToolFailureReason` (:29), `ToolFailurePolicy` (:47), `ToolFailure` (:66); enforcement in `tools/tool_usage.py`; contextvar policy switching in same module.
**Signature:** tool `_run`/`_arun` returns `ToolFailure` (frozen BaseModel) instead of an error string; reasons: `tool_reported | exception | mcp_error | usage_limit | unknown_tool | invalid_input`; policies: `ignore | warn (default) | raise`.
**Data Shape:** Detection is STRICTLY DECLARATIVE — a returned ToolFailure instance; nothing inspects whether output text "looks like" an error.

### Decisive source
```python
# :1 module docstring states the contract verbatim
"""A tool can complete without raising and still fail: Slack answers ``HTTP 200``
with ``{"ok": false, ...}``, an MCP server sets ``isError``. The call
"worked", so the error used to reach the agent as an ordinary string and the
run was recorded as a success.

A tool declares failure by returning a :class:`ToolFailure`; the policy
(:class:`ToolFailurePolicy`) decides the reaction. Detection is strictly
declarative -- nothing here guesses whether a string "looks like" an error."""

# :47 policy semantics
IGNORE = "ignore"   # pre-1.16 behavior: not recorded, emitted, or acted on
WARN   = "warn"     # record + emit + keep going. The default.
RAISE  = "raise"    # record + emit, then abort with ToolExecutionFailedError
```

**Flow:** tool returns ToolFailure(reason=...) → framework records + emits failure events per active policy → agent still receives text via `as_agent_message()` so MODEL BEHAVIOR is unchanged; only observability/control changes → `raise` policy converts to ToolExecutionFailedError abort. Usage-limit/unknown-tool/invalid-input arms reuse the same channel for framework-detected failures.
**Invariant:** Frozen model = reports are immutable evidence. The default MUST stay warn: flipping default to raise breaks every crew whose model recovers from failed calls conversationally. Never add heuristic string detection — the docstring forbids it because false positives corrupt runs recorded as successes.
**Probe:** `grep -c 'TOOL_REPORTED\|MCP_ERROR\|USAGE_LIMIT' lib/crewai/src/crewai/tools/tool_failure.py` → counts lines ≥3; direct suite: `/tmp/crewai-p1-venv/bin/python -m pytest tests/tools/test_tool_failure.py -q -p no:xdist -o addopts=''` → `97 passed, 2 skipped` (PlatformActionTool pair needs crewai-tools installed).
**Direct test:** `tests/tools/test_tool_failure.py::test_ok_response_still_returns_json` / `::test_non_ok_response_becomes_a_tool_failure` pin the HTTP-200-ok:false boundary.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-crewAI", query: "ToolFailurePolicy ignore warn raise tool reported failure", limit: 5 });
// → ext-crewAI...tools.tool_failure.ToolFailurePolicy Class tool_failure.py 47+
```

## Verdict
Adopt the return-a-TypedFailure-object protocol for any integration where APIs signal failure inside success envelopes. Adapt reason enum to host domains. Omit CrewAI's platform-action tool implementations.
