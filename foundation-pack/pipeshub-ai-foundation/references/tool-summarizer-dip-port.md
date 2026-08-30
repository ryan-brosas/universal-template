<!-- capsule-v2 -->
# Tool summarizer DIP port — how does the generic library render human-readable activity without importing the product layer?

**Source:** pipeshub-ai Apache-2.0 `main@4a02110dd9a7a644d8ba7a5ccd295c58a3c3628f`; Codebase Memory `pipeshub-ai`. **Question:** Where do per-tool pretty summaries live so the framework stays dependency-clean yet the UI gets rich descriptions?

## ToolSummarizer Protocol injected onto AgentRuntime; missing/buggy implementations degrade to empty, never raise
**Path/Symbol:** `backend/python/app/agent_loop_lib/tools/summarizer.py:ToolSummarizer/ToolCallSummary/ArgsFormatter/ResultFormatter` (L32–74); injection site `runtime/runtime.py:94` (`summarizer: ToolSummarizer | None = None`); concrete impl `app/agents/agent_loop/tool_summarizer.py:PipesHubToolSummarizer` wired by factory; LLM-backed variant via `control_plane.py:641 make_llm_summarizer`.
**Signature:** Protocol methods `summarize_args(tool_name: str, args: dict) -> str | None` and `summarize_result(tool_name, args, result: ToolResult) -> ToolCallSummary`; formatters `Callable[[dict], str | None]` / `Callable[[dict, ToolResult], str | None]` shared with `@tool(args_summary=..., result_summary=...)` declarations.
**Data Shape:** `ToolCallSummary(args_summary: str | None, result_summary: str | None)` — every field optional; additive payload alongside (never replacing) raw truncated previews in AgentEvents.

### Decisive source
```python
# The module docstring states both failure modes the design absorbs:
"""1. A missing summarizer (runtime.summarizer is None, e.g. ControlPlane
   standalone agents that never wire one) — every field on ToolCallSummary
   is optional so "no summary" is just the empty default, never an error.
2. A buggy per-tool formatter — implementations are expected to catch their
   own exceptions and degrade to an empty ToolCallSummary ... callers must
   not assume summarization can fail."""
# summarize_result contract:
"""A short description of both the args and the outcome, computed from the
   FULL result.content/result.sources — must be called BEFORE any truncation
   is applied to the result being described."""
```

**Flow:** tool_loop calls through the Protocol only → args summaries come from the small LLM-authored dict (cheap); result summaries are computed from the FULL result BEFORE truncation → summary rides event payloads additively → frontends/persisted messages keep consuming unchanged raw previews.
**Invariant:** (1) Dependency arrow points library←product: `agent_loop_lib` never imports `app/agents`; the concrete summarizer is injected at runtime assembly (same DIP shape as spec_factory). (2) Summaries are best-effort decoration — absent summarizer, unknown tool, malformed JSON, or a raising formatter all yield empty/default output, never an exception into the turn loop. (3) Result summaries must see the UNTRUNCATED content — calling after truncation silently degrades every description. (4) One formatter shape serves two call sites (@tool declarations and name-keyed fallback registry) so a formatter written for either drops in.
**Probe:** `tests/unit/agents/adapter/test_tool_summarizer.py` — :88/:97 unknown-tool generic fallbacks, :107 malformed-JSON no-raise, :114 None-result no-raise, :121 formatter-exception graceful degradation. Precedence over decorator-declared summaries pinned by `tests/unit/agent_loop_lib/agent/test_tool_loop_summary_precedence.py`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pipeshub-ai", query: "ToolSummarizer ToolCallSummary PipesHubToolSummarizer summarize_result", limit: 8, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the Protocol-injection port + total-degradation contract + summarize-before-truncate ordering for any host/tool integration boundary. Adapt concrete formatters per connector. Omit the LLM-backed summarizer flavor if the host has no cheap model tier (the None default covers it). No coverage caveat.
