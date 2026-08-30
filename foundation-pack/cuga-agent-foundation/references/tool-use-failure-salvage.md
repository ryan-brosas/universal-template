<!-- capsule-v2 -->
# Provider tool-call failure recovery (Groq tool_use_failed) — how do you salvage the code a model emitted into the tool-call channel when the provider rejects the request?

**Source:** cuga-agent Apache-2.0 `main@5de53ade77c36166da6ace906af488b2b445454f`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** Providers like Groq 400-reject with `tool_use_failed` + `failed_generation` when the model emits a spurious tool call — how do you detect that error and recover the generation as executable sandbox code?

## Detect both stringified and structured-body forms; parse failed_generation JSON (with single-quote repair); convert to fenced python
**Path/Symbol:** `src/cuga/backend/llm/errors.py` — `_parse_failed_generation_json` :13-20, `_parse_tool_use_failed_from_body` :23-37, `is_tool_choice_none_tool_use_failed` :40-59, `is_ollama_tool_call_parse_error` :62-70, `ainvoke_with_retry_on_tool_choice_none` :73-88, `parse_tool_use_failed_generation` :91-121, `failed_gen_to_code` :124-143, `extract_code_from_tool_use_failed` :146-155. Consumer: `adapter/graph_adapter.py:125-142` (`ainvoke_model` catch → `_FakeResponse(content=f"```python\\n{code}\\n```")`).
**Signature:** `extract_code_from_tool_use_failed(err) -> Optional[str]` (code or None); `is_tool_choice_none_tool_use_failed(err) -> bool`; `failed_gen_to_code(failed_gen: dict) -> Optional[str]`.
**Data Shape:** failed_generation = `{name, arguments}`; `name == "python"` with STRING arguments ⇒ arguments ARE the code (`\\n` unescaped); named tools ⇒ `result = await {name}({k}={v!r}, ...)\nprint(result)`.

### Decisive source
```python
# :107-120 — string-form regex ladder + last-ditch brace fallback for
# malformed JSON that still contains '"name": "python"'
if "failed_generation" not in err_str or "tool_use_failed" not in err_str: return None
m = re.search(r"'failed_generation':\s*'([^']+)'", err_str)
...
if not failed_gen and '"name": "python"' in raw_fg:
    arg_m = re.search(r'"arguments":\s*(.+?)\s*\}', raw_fg, re.DOTALL)
    if arg_m: failed_gen = {"name": "python", "arguments": arg_m.group(1).strip()}
```
```python
# graph_adapter.py:129-141 — recovery point: exception → fake AIMessage so the
# sandbox node runs the salvaged code through the NORMAL pipeline
code = extract_code_from_tool_use_failed(exc)
if code:
    class _FakeResponse: content = f"```python\\n{code}\\n```"; additional_kwargs = {}
    return _FakeResponse()
```
**Flow:** ainvoke raises → check recoverable? (`tool_use_failed`+`Tool choice is none` strings OR structured body dict) / Ollama `"error parsing tool call"` → retry same call once (`ainvoke_with_retry_on_tool_choice_none`) → else try salvage: body-dict first, then stringified regex (+ escaped-quote repair), then convert to code → wrap as fake response → normal extraction/sandbox path. Non-matching errors re-raise untouched.
**Invariant:** (1) Recovery is BEST-EFFORT and additive — any doubt returns None and the original exception propagates. (2) The fake response must carry FENCED python so downstream extraction treats it exactly like model output (print-gate applies). (3) Retry-vs-salvage are distinct responses: retryable = provider rejected a spurious call; salvageable = provider rejected but emitted usable generation.

**Probe:** `tests/unit/test_tool_use_failed_recovery.py` — `test_groq_python_tool_single_quotes` (:20), `test_malformed_json_python_fallback` (:52), `test_parses_exception_body_when_string_format_is_unhelpful` (:75), `test_groq_python_e2e` (:150), `test_non_recoverable_returns_none` (:172).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "extract_code_from_tool_use_failed failed_generation groq tool_use_failed", limit: 8 });
```
## Verdict
Adopt the two-channel detection (string + body) plus fake-response salvage whenever models emit into tool channels on providers that reject them. Adapt regexes per provider error format.
