<!-- capsule-v2 -->
# Retry-prompt rendering — what exact text does the model receive for validation errors and retries?

**Source:** pydantic-ai MIT `main@b3cdbc96796f0294f1ac6943cdba70d14af8a0ef`; Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** How are ValidationError details vs ModelRetry messages rendered into the corrective prompt, and which fields get excluded so the model isn't shown redundant input?

## `RetryPromptPart.from_error` + `RetryPromptPart.model_response`
**Path/Symbol:** `pydantic_ai_slim/pydantic_ai/messages.py:RetryPromptPart.from_error` (:1669–1690), `RetryPromptPart.model_response` (:1692–1714).
**Signature:** `from_error(cls, error: ValidationError | ModelRetry, *, tool_name: str | None = None, tool_call_id: str | None = None) -> RetryPromptPart`; `model_response(self) -> str`.
**Data Shape:** `content: list[ErrorDetails] | str` — list when built from a Pydantic ValidationError, str when from a `ModelRetry.message`. The same part serves six retry triggers (args validation, tool ModelRetry, unknown tool, text-when-structured-expected, output validation, output-validator retry).

### Decisive source
```python
# messages.py:1700-1709 — exclusion matrix keyed on whether the generated JSON is already in context
if self.tool_name is None:
    # NativeOutput retries: the generated JSON is already in the model's context,
    # so top-level errors' `input` just duplicates it.
    exclude = {i: {'ctx', 'input'} if len(e.get('loc', ()) ) <= 1 else {'ctx'}
               for i, e in enumerate(self.content)}
else:
    # Tool-call retries keep `input`: the model must see WHAT arguments it sent.
    exclude = {'__all__': {'ctx'}}
json_errors = error_details_ta.dump_json(self.content, exclude=exclude, indent=2)
plural = isinstance(self.content, list) and len(self.content) != 1
description = f'{len(self.content)} validation error{"s" if plural else ""}:\n```json\n{json_errors.decode()}\n```'
```

**Flow:** error raised anywhere in validate/execute → agent loop calls `from_error` (the ONE construction path — anything else presenting the failure, like instrumentation spans, must build the identical part) → ValidationError becomes `.errors(include_url=False, include_context=False)`; ModelRetry stays its message string → on render: string content prefixed `'Validation feedback:\n...'` only when `tool_name is None`; list content dumped as fenced JSON with the exclusion matrix applied; always suffixed `'\n\nFix the errors and try again.'`.

**Invariant:** This is the exact message the model receives when the error is handled by the agent loop, so every parallel presenter must match it byte-for-byte. The exclusion asymmetry is load-bearing: for native-output retries the schema-generated JSON already sits in the model's context, so echoing top-level `input` duplicates it; for tool-call retries the input IS the diagnostic (what arguments did I send wrong?). Nested errors (loc length > 1) keep their `input` even on native-output retries because nested paths aren't visible at the top level.

**Probe:** `tests/test_messages.py` RetryPromptPart rendering tests pin both branches of the exclusion matrix and the fenced-JSON format; `tests/test_agent.py` output-validation retry tests exercise `tool_name=None` native-output path end-to-end.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pydantic-ai", query: "RetryPromptPart from_error model_response error_details_ta", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the single-construction-path discipline and the input-exclusion asymmetry between native-output and tool-call retries; adopt the fenced-JSON error dump with count line and fixed suffix. Adapt wording to your framework's voice. Omit nothing — exclusions that leak duplicated input measurably confuse small models.
