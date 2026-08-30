<!-- capsule-v2 -->
# Ask-user-question eager SSE — why must an interactive tool's payload be emitted from a POST_TOOL_USE hook instead of the final answer?

**Source:** pipeshub-ai Apache-2.0 @ `main` (pin `6850972`); Codebase Memory `mnt-hdd-utopia-inspo-platforms-pipeshub-ai`. **Question:** interactive option cards need the question payload BEFORE any answer_chunk/complete — how does the agent-loop path reproduce nodes.py's eager emission and its once-only flag?

## Name-aliased trigger + shared emitted flag
**Path/Symbol:** `backend/python/app/agents/agent_loop/hooks/ask_user_question.py:27-61` (`ask_user_question_sse`, wired POST_TOOL_USE `factory.py:924`).
**Signature:** `ask_user_question_sse(context) -> Middleware[ToolResultContext]`; `_ASK_USER_QUESTION_TOOL_NAMES = {"internaltools__ask_user_question", "internaltools_ask_user_question", "internaltools.ask_user_question"}`.
**Data Shape:** emits via `context.formatter.ask_user_question(context, status=..., tool_data=payload)` events; sets `tool_state["ask_user_question_emitted"] = True` — the SAME flag nodes.py's end-of-turn fallback emitter checks.

### Decisive source
```python
tool_name = resolve_tool_name(ctx)
if tool_name not in _ASK_USER_QUESTION_TOOL_NAMES:
    return
if context.event_sink is None or not context.has_ui_client:
    return
output = ctx.tool_response
raw_result = output.data if output.success else output.error
payload: Any = raw_result
if isinstance(raw_result, str):
    try:
        payload = json.loads(raw_result)
    except (json.JSONDecodeError, TypeError):
        payload = raw_result
```

**Flow:** POST → resolve_tool_name (registry-backed with path-segment fallback, see _tool_naming capsule) → match against the three historical spellings → skip silently when no sink or non-UI client → parse string results leniently → emit formatter events → set the shared flag so the fallback emitter no-ops exactly as on the legacy LangGraph path.
**Invariant:** emission happens the moment the result exists — before RespondPipeline synthesizes anything — so the frontend can render cards and suppress plain-text answers. The name set absorbs serialization drift across registry generations rather than normalizing at one site. Error results are still emitted (status="error") — a failed ask must surface, not vanish.

### Direct test
**Probe:** `tests/unit/agents/adapter/test_ask_user_question.py` + `tests/unit/agents/adapter/test_clarification.py` — execute `/tmp/psh17venv/bin/python -m pytest tests/unit/agents/adapter/test_ask_user_question.py tests/unit/agents/adapter/test_clarification.py -q` (passed at pin).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-pipeshub-ai", query: "ask_user_question_sse eager emission event_sink has_ui_client", limit: 4, fields: ["signature", "name", "file"] });
// resolves hooks/ask_user_question.py symbols line-exact
```

## Verdict
Adopt hook-level eager emission for interactive-tool payloads plus the shared-flag contract that makes later fallbacks idempotent. Adapt name vocabulary, formatter, and UI-client gating. Omit nodes.py legacy internals beyond the flag contract.
