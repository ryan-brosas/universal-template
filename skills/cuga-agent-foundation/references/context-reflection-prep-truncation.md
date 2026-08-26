<!-- capsule-v2 -->
# Reflection context prep + truncation markers — how do you shrink chat history and execution output for a secondary prompt, and what must the marker format preserve?

**Source:** cuga-agent Apache-2.0 `main@5de53ade77c36166da6ace906af488b2b445454f`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** How does `prepare_reflection_context` compose summarization with hard char caps, and why is the trim marker appended INSIDE the budget?

## Summarize messages first (temp-state path), THEN cap both history and output to char budgets
**Path/Symbol:** `src/cuga/backend/cuga_graph/utils/context_management_utils.py:18-65` (`truncate_text_for_context`, `messages_to_history_text`, `prepare_reflection_context`).
**Signature:** `truncate_text_for_context(text, max_chars, *, label="content") -> str`; `messages_to_history_text(messages) -> str`; `async def prepare_reflection_context(chat_messages, coder_agent_output, model, *, max_output_chars, max_history_chars, tracker=None) -> tuple[str, str]`.
**Data Shape:** truncated text = `trimmed[:max_chars] + "...\n\n[{label} trimmed to {max_chars} chars]"` — marker counts toward the final length; empty/None input normalizes to "" via `(text or "").strip()`; `max_chars <= 0` or short input → no-op. History lines: `User: ...` / `Assistant: ...` / `{ClassName}: {content}`; empty list → literal `"No previous conversation history"`.

### Decisive source
```python
# context_management_utils.py:22-23 and :49-64
return f"{trimmed[:max_chars]}...\n\n[{label} trimmed to {max_chars} chars]"
...
summarized = await apply_context_summarization(
    list(chat_messages), model, tracker=tracker,
    message_list_name="chat_messages",   # NOT the main-loop list
)
history = truncate_text_for_context(messages_to_history_text(summarized),
                                   max_history_chars, label="Agent history")
output = truncate_text_for_context(coder_agent_output,
                                   max_output_chars, label="Execution output")
return history, output
```
Ordering matters: token-aware SUMMARIZATION runs on the message objects first (via the temp-state wrapper — see knowledge capsule `context-summarization-temp-state`), then plain CHAR truncation bounds the rendered text for the reflection prompt. A defensive `list(...)` copy prevents the temp-state path from aliasing the caller's list. Failure metrics detection rides `_log_and_track_metrics`, which detects failure BY KEY PRESENCE (`"error" in metrics`) because `str(exception)` can be empty (:176-184).

**Flow:** copy chat_messages → apply_context_summarization (never raises; falls back to originals) → render role-prefixed history text → char-truncate with labeled marker → same truncation for execution output → return (history, output) tuple.
**Invariant:** The two-stage design (semantic summarize → mechanical cap) means char budgets are a LAST-RESORT guard, not the primary compressor; the marker must be self-describing (what was trimmed, to what) because reflection prompts feed eval analysis; unknown message types render by class name rather than being dropped — losing a ToolMessage silently corrupts reflection quality.

**Probe:** `tests/unit/test_context_management_utils.py` — no-op-when-short :9, marker-added :14, role formatting :21, failure-metrics-with-empty-error-message :31.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "prepare_reflection_context truncate_text_for_context messages_to_history_text", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the summarize-then-cap ordering and labeled self-describing trim markers for any secondary prompt assembly. Adapt labels/budgets. Omit the role formatter if your summaries are already flat text. Direct tests exist.
