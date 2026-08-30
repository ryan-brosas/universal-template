<!-- capsule-v2 -->
# Rich-console safety & monitor — how do arbitrary tool payloads reach the terminal without crashing markup, and what does the step monitor accumulate?

**Source:** smolagents Apache-2.0 `main@30bb1161`; Codebase Memory `ext-smolagents`. **Question:** Why is `sanitize_for_rich` applied to task/log text, and exactly which counters does Monitor keep per run?

## Text-not-markup discipline
**Path/Symbol:** `src/smolagents/utils.py:sanitize_for_rich` (:64-89); `src/smolagents/monitoring.py:Monitor.update_metrics` (:100-117), `AgentLogger.log_task` (:200-218, in-source comment IS the rationale), `log_error` (:149-150), LogLevel IntEnum (:120-124).
**Signature:** `sanitize_for_rich(value) -> str` (bytes→utf8-replace; control chars → `\xNN`; newline/tab/CR preserved); `Monitor(tracked_model, logger)` with `step_durations:list`, `total_input_token_count`, `total_output_token_count`.
**Data Shape:** Log levels OFF=-1/ERROR=0/INFO=1/DEBUG=2 (IntEnum so `level <= self.level` works); per-step console line: `[Step N: Duration X.XX seconds| Input tokens: ...| Output tokens: ...]`.

### Decisive source
```python
# :201-204 — the comment documents the crash class this prevents:
# Important: `content` can contain arbitrary tool logs / payloads. If we embed it
# inside Rich markup (e.g. f"[bold]{content}"), any stray "[/...]" sequences or
# binary-ish characters can crash Rich's markup parser. Render the content as
# `Text` instead, and apply styling via Text/style, not markup.
safe_content = sanitize_for_rich(content)
```

**Flow:** Every agent-visible payload path routes through either Text() rendering (log_task, observations log in agents.py with `[` → `|` escaping for rich-tag-like components) or sanitize_for_rich (error text). Monitor hooks the step-callback registry as an ActionStep subscriber (backward-compat arity), appending each step's duration and ADDING token_usage into running totals only when present (`None` usage steps still append duration). RunResult later refuses a total when ANY step lacks usage (`correct_token_usage` flag) rather than summing partials.
**Invariant:** Styling lives in wrappers, never interpolated user strings — the invariant survives any console backend swap. Partial-usage honesty: totals are None-inclusive-of-gap, not best-effort sums.
**Probe:** `tests/test_monitoring.py::test_monitor_update_metrics`-style cases + `tests/test_agents.py::test_no_token_usage` (:927-951, asserts usage=None propagation). Live: feed Monitor two steps (100/10 then 30/5) → totals 130/15/145.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-smolagents", query: "sanitize_for_rich Monitor update_metrics TokenUsage", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt render-as-Text for all untrusted console output. Adapt the escape table to your renderer. Keep the honest None-on-partial-usage rule — silently dropping gaps misprices runs.
