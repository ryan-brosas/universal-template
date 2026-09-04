<!-- capsule-v2 -->
# Empty-response completion gate — how do you recover from a model turn with no text and no tool calls without infinite nudging?

**Source:** pipeshub-ai Apache-2.0 @ `main` (pin `6850972`); Codebase Memory `mnt-hdd-utopia-inspo-platforms-pipeshub-ai`. **Question:** what should the loop do when the model returns an empty response — fail, retry blindly, or nudge?

## POST_MODEL recovery_message with tree-wide bounded nudges
**Path/Symbol:** `backend/python/app/agents/agent_loop/hooks/completion_gate.py:38-61` (`completion_gate`, wired POST_MODEL at `factory.py:932`).
**Signature:** `completion_gate(context, *, max_nudges: int = 2) -> Middleware[ModelResponseContext]`.
**Data Shape:** sets `ctx.recovery_message = UserMessage(content=..., injected=True)` — the same mechanism `truncation_recovery.py` established; Agent.step() injects it and continues instead of succeeding.

### Decisive source
```python
async def _middleware(ctx: ModelResponseContext, next_fn: "Next") -> None:
    await next_fn()
    if ctx.tool_calls or getattr(ctx.response, "truncated", False):
        return
    text = _response_text(ctx.response)
    if text.strip():
        return
    if context.completion_gate_nudges >= max_nudges:
        return
    context.completion_gate_nudges += 1
    ctx.recovery_message = UserMessage(content=_EMPTY_RESPONSE_NUDGE, injected=True)
```

**Flow:** POST_MODEL → tool calls or text present ⇒ healthy, return → truncated responses are LEFT ALONE (recovery belongs to truncation handling) → empty response under budget increments the counter and requests injection of a system nudge offering exactly two exits (call a tool OR answer in text).
**Invariant:** `context` is the SAME AgentContext threaded through top-level agent AND every spawned child, so `completion_gate_nudges` is counted TREE-WIDE, not per-agent — a port that counts per-agent lets each subtree spend the full budget. The gate never fabricates content; it only re-prompts.

### Direct test
**Probe:** `tests/unit/agents/adapter/test_completion_gate.py::test_bounded_by_max_nudges` :64, `.test_skips_truncated_response` :75, `.test_works_without_a_scope` :82. Execute: `/tmp/psh17venv/bin/python -m pytest tests/unit/agents/adapter/test_completion_gate.py -q` (7 passed at pin).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-pipeshub-ai", query: "completion_gate empty response nudge recovery_message max_nudges", limit: 4, fields: ["signature", "name", "file"] });
// rank hits test_completion_gate.py tests + hooks/completion_gate.py symbols
```

## Verdict
Adopt bounded tree-wide nudging via the existing recovery-message channel for empty model turns. Adapt nudge copy and budget to your loop. Omit any separate responder-LLM fallback (this plane's whole point is that the ReAct turn itself is the answer source).
