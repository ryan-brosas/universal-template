<!-- capsule-v2 -->
# Summary fallback — ordered models for compaction recovery

**Source:** Aider Apache-2.0 `main@5dc9490bb35f9729ef2c95d00a19ccd30c26339c`; Codebase Memory project `aider` (full). **Question:** When history compaction needs a model call, how can a harness recover from a failed preferred summarizer without returning an unlabelled or partially formed history?

## Ordered fallback with one normalized result
**Path/Symbol:** `ChatSummary.summarize_all(messages)` (`aider/history.py:98-123`).
**Signature:** `summarize_all(messages) -> list[dict[str, str]]`.
**Data Shape:** input messages are role/content dictionaries; only `USER` and `ASSISTANT` turns form the summary input; `self.models` is an ordered fallback list; the successful result is one synthetic `user` message prefixed as prior-history summary.

### Decisive source
```python
for model in self.models:
    try:
        summary = model.simple_send_with_retries(summarize_messages)
        if summary is not None:
            summary = prompts.summary_prefix + summary
            return [dict(role="user", content=summary)]
    except Exception as e:
        print(f"Summarization failed for model {model.name}: {str(e)}")
raise ValueError("summarizer unexpectedly failed for all models")
```

**Flow:** serialize eligible turns under explicit role headers; build a fixed system-plus-user summary request; try models in declared order; continue after an exception or `None`; normalize the first successful result with a stable history prefix and one role; fail loudly only after every candidate is exhausted.
**Invariant:** fallback preserves the configured ordering, never returns a partial summary, and makes the compressed history recognizable before it re-enters the prompt.
**Probe:** `tests/basic/test_history.py::TestChatSummary.test_fallback_to_second_model` (`:83-120`) makes the first model raise, asserts both models were tried once, and asserts the second result has the expected prefix and `user` role. Direct runner unavailable; inspected source and direct test.

## Retrieve
```ts
await mcp.codebase_memory.search_graph({
  project: "aider",
  query: "summarize_all fallback second model",
  file_pattern: "aider/history.py",
  limit: 10,
  fields: ["signature"]
});
```

## Verdict
Adopt ordered summarizer fallback and normalize the first successful output into one explicit history message. Adapt the model list, telemetry, and prompt text; omit Aider's transport and console wording.
