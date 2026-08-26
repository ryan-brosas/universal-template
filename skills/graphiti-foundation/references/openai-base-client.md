<!-- capsule-v2 -->
# OpenAIClient base — reasoning-effort sentinel, dual response parsers, self-correcting retry

**Source:** graphiti MIT `main@401c59a6`; Codebase Memory `graphiti`. **Question:** how does the OpenAI-family base client resolve the `'auto'` reasoning sentinel, parse two different response shapes, and retry with conversational self-correction — and which failures are NOT retried?

## Connected graph-selected seam
**Path/Symbol:** `graphiti_core/llm_client/openai_base_client.py:BaseOpenAIClient` (:42–334); `_resolve_reasoning_effort` (:118–144), `_handle_structured_response` (:146–166), `_handle_json_response` (:168–183), `_generate_response` (:185–239), `generate_response` (:241–334); `llm_client/errors.py` (`RateLimitError`, `RefusalError`).
**Signature:** `async generate_response(messages, response_model=None, max_tokens=None, model_size=ModelSize.medium, group_id=None, prompt_name=None, *, attribute_extraction=False) -> dict`; `MAX_RETRIES: ClassVar[int] = 2`.
**Data Shape:** subclasses implement ONLY `_create_completion` / `_create_structured_completion` (abstract); the base owns message conversion, model-size routing, reasoning/verbosity resolution, response parsing, token accounting, and the manual retry loop. `cache=True` raises `NotImplementedError` (OpenAI-family has no cache). Defaults: `DEFAULT_MODEL='gpt-5.5'`, `DEFAULT_SMALL_MODEL='gpt-4.1-nano'`, `DEFAULT_REASONING='auto'`, `DEFAULT_VERBOSITY='low'`, `DEFAULT_MAX_TOKENS=16384`.

### Decisive source
```python
def _resolve_reasoning_effort(model, reasoning):
    if reasoning != 'auto':
        return reasoning              # explicit override always wins
        # 'auto' is a sentinel, never sent to the API
    if model.startswith('gpt-5.5'):
        return 'none'                 # reasoning OFF: cheapest for structured extraction
    return 'minimal'                 # cheapest broadly-supported tier (NOT None)
```

```python
# _handle_structured_response — Responses API token fields
input_tokens = getattr(response.usage, 'input_tokens', 0) or 0
output_tokens = getattr(response.usage, 'output_tokens', 0) or 0
return json.loads(response.output_text), input_tokens, output_tokens
# _handle_json_response — Chat Completions token fields
input_tokens = getattr(response.usage, 'prompt_tokens', 0) or 0
output_tokens = getattr(response.usage, 'completion_tokens', 0) or 0
```

**Flow:** `generate_response` prepends the attribute-extraction preamble, appends the group-id language instruction to `messages[0]`, opens an `llm.generate` tracing span, then loops up to `MAX_RETRIES+1` times. On success it accumulates tokens and records them to the token tracker. `RateLimitError`/`RefusalError` re-raise immediately (never retried). `openai.APITimeoutError`/`APIConnectionError`/`InternalServerError` re-raise (OpenAI client handles them). **Any other `Exception`** appends a self-correcting user message to the conversation (`error_context` — error class name + details + "Please try again with a valid response") and retries, up to the cap.
**Invariant:** (1) `'auto'` is a local sentinel resolved per-model and never transmitted; returning `'minimal'` (not omitting) prevents non-gpt-5.5 reasoning models from silently jumping to the API's pricier default effort; (2) the two parsers read DIFFERENT token field names (`input_tokens`/`output_tokens` vs `prompt_tokens`/`completion_tokens`) — porting one parser for both shapes corrupts usage accounting; (3) the retry loop is manual (not tenacity) and feeds error context back into the model, so only genuinely recoverable application errors reach it.
**Probe:** `tests/llm_client/test_openai_client.py:46` `test_default_model_and_reasoning_sentinel` + `:52-71` `test_resolve_reasoning_effort` (matrix: `('gpt-5.5','auto','none')`, `('gpt-5.5-2026-04-23','auto','none')`, `('gpt-5','auto','minimal')`, `('gpt-5.4-mini','auto','minimal')`, `('o1','auto','minimal')`, `('gpt-5.5','high','high')`, `('gpt-5.5',None,None)`); `:107` `test_explicit_reasoning_overrides_auto`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "graphiti", query: "_resolve_reasoning_effort _handle_structured_response _handle_json_response MAX_RETRIES", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the `'auto'`-sentinel reasoning resolution (prefix-match gpt-5.5 → `none`, else → `minimal`, explicit override wins) and the dual-parser token-field split verbatim; adapt the manual self-correctoring retry loop's attempt cap to your SLO; omit the OpenAI-specific exception classes if you don't use the openai SDK. Note: this capsule is a COMPLEMENT to `llm-client.md` (the abstract tenacity layer in `client.py`); the OpenAI-family base adds the reasoning sentinel, dual parsers, and conversational retry on top of that shared contract.
