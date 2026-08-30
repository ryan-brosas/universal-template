<!-- capsule-v2 -->
# Generic-client structured output ladder — json_schema default, json_object prompt-injection fallback

**Source:** graphiti MIT `main@401c59a6`; Codebase Memory `graphiti`. **Question:** how should one OpenAI-compatible chat-completions client serve both constrained-decoding servers and providers without native json_schema — and survive their fence-wrapped, empty, and flaky responses?

## Connected graph-selected seam
**Path/Symbol:** `graphiti_core/llm_client/openai_generic_client.py:OpenAIGenericClient.__init__` (:60–100, `structured_output_mode` param), `_build_response_format` (:102–124), `_strip_code_fences` (:126–138), `_generate_response` (:140–174, empty-body guard :162–166), `generate_response` json_object injection (:191–200).
**Signature:** `OpenAIGenericClient(config=None, cache=False, client=None, max_tokens=16384, structured_output_mode='json_schema' | 'json_object')`.
**Data Shape:** targets any OpenAI-compatible `/chat/completions` endpoint (vLLM, llama.cpp, Ollama, DeepSeek, Together). `response_format` payload is either `{'type': 'json_object'}` or `{'type': 'json_schema', 'json_schema': {'name': ..., 'schema': model_json_schema()}}`.

### Decisive source
```python
def _build_response_format(self, response_model):
    if response_model is None or self.structured_output_mode == 'json_object':
        return {'type': 'json_object'}
    # We intentionally OMIT "strict": true — strict mode requires OpenAI's
    # strict subset (additionalProperties: false, every field required), which raw
    # model_json_schema() routinely violates. Adherence is best-effort on
    # OpenAI-proper; constrained-decoding servers (vLLM, llama.cpp) still enforce it.
    return {'type': 'json_schema',
            'json_schema': {'name': getattr(response_model, '__name__', 'structured_response'),
                            'schema': response_model.model_json_schema()}}

if not result:
    raise EmptyResponseError('LLM returned an empty response')   # before json.loads('')
return json.loads(self._strip_code_fences(result))
```

**Flow:** mode=json_schema → API enforces the schema, NO prompt injection; mode=json_object → schema serialized into the LAST message (`'\n\nRespond with a JSON object in the following format:\n\n{schema}'`) since the API won't enforce anything; either way the body is fence-stripped (regex peels ```` ```lang\n ```` head + tail) then parsed; empty body raises `EmptyResponseError` instead of a cryptic JSONDecodeError.
**Invariant:** (1) never set `"strict": true` with raw Pydantic schemas — it 400s; (2) `EmptyResponseError` is classified TRANSIENT by the base retry (`is_server_or_retry_error`) because empty bodies are usually flaky local endpoints; (3) openai.RateLimitError is translated to graphiti's own RateLimitError at the `_generate_response` boundary; (4) non-retryable errors propagate after exactly ONE create call — the old hand-rolled re-prompt loop was deliberately removed in favor of the base tenacity wrapper.
**Probe:** `tests/llm_client/test_openai_generic_client.py:61 defaults_to_json_schema`, `:73 json_schema_mode_does_not_inject_schema_into_prompt`, `:84 json_object_mode_uses_json_object_and_injects_schema`, `:98 no_response_model_uses_json_object_without_injection`, `:112 rate_limit_error_is_translated`, `:128 empty_content_raises_empty_response_error`, `:139 empty_response_error_is_retryable`, `:148 strips_markdown_code_fence_before_parsing`, `:160 non_retryable_error_is_not_retried` (asserts exactly 1 create call).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "graphiti", query: "OpenAIGenericClient structured_output_mode _strip_code_fences EmptyResponseError", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the two-mode ladder + omission of `strict:true` + fence-strip-then-parse pipeline verbatim for any OpenAI-compatible integration; adapt max_tokens default upward for local models (16384 here vs 4096 base); omit the json_object mode only if you control the serving stack end-to-end.
