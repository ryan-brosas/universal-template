<!-- capsule-v2 -->
# Summarization hard-truncation fallback — what happens when the summary LLM call itself fails, and why is langchain pinned <1.3.15?

**Source:** cuga-agent Apache-2.0 `main@5de53ade77c36166da6ace906af488b2b445454f`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** When the summarization model call fails, how must the fallback behave so downstream eval/tracker consumers can still find affected tasks — and what does the `[-0:]` footgun have to do with it?

## Hard truncation on middleware failure
**Path/Symbol:** `src/cuga/backend/cuga_graph/utils/context_summarizer.py:315-348` (`summarize_messages` except block) + `_invoke_middleware` error wrapping (:466-482).
**Signature:** `summarize_messages(self, messages) -> Tuple[List[BaseMessage], Dict[str, Any]]` — metrics dict carries `"hard_truncation": True` plus counts on failure.
**Data Shape:** Failure metrics: `{error, fallback, hard_truncation, messages_dropped, messages_kept, message_count_before, token_count_before}`; success metrics carry `before/after/tokens_saved/compression_ratio`.

### Decisive source
```python
# context_summarizer.py:328-332
# Hard truncation is the maximal state-loss mode (dropped IDs, variables,
# partial results) — signal it loudly with counts, and return metrics rich
# enough for the tracker/eval analysis to find affected tasks (issue #563).
# keep_n <= 0 must keep nothing: messages[-0:] would return the WHOLE list.
kept_messages = messages[-keep_n:] if keep_n > 0 else []
```
The langchain pin rationale (docstring :414-437, measured): versions ≤1.3.14 catch the summary-model failure INSIDE the middleware and return the text `"Error generating summary: ..."` as a normal summary — you get a placeholder message and success-shaped metrics. 1.3.15 retries then raises; `_invoke_middleware` wraps it as `RuntimeError("middleware_invocation_failed: ...")` which this except catches → hard truncation + honest metrics. Both lose the same history; only the REPORTING differs. The cap exists so a security-driven dep bump can't silently change behavior.

**Flow:** middleware raises (or ≤1.3.14 returns placeholder-as-success) → except computes `kept = messages[-keep_n:] if keep_n > 0 else []` → logs dropped/kept counts → returns `(kept, failure_metrics)` → `_log_and_track_metrics` (context_management_utils.py:178-184) detects failure BY KEY PRESENCE (`"error" in metrics or metrics.get("hard_truncation")` — not truthiness, since `str(exc)` may be empty) → emits tracker step `ContextSummarizationFailure` for eval analysis.
**Invariant:** A summarization failure must degrade to recent-messages-only WITHOUT raising to the caller, but it must never be reportable as a successful summarize; failure detection uses key presence because exception strings can be empty.

**Probe:** `tests/unit/test_context_summarizer.py::test_model_error_handling / test_empty_summary_response` — pins the failure path returning kept-recent messages with error metrics.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "summarize_messages hard_truncation middleware_invocation_failed", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the hard-truncation fallback shape (keep recent, loud failure metrics, key-presence detection) and the `[-0:]`-guard comment pattern. Adapt the tracker event name. Omit the version pin once your middleware reports failures honestly. Direct tests exist.
