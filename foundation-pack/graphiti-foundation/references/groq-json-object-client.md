<!-- capsule-v2 -->
# Groq json-object client — how do you port a minimal OpenAI-compatible chat provider, and what does the base-class contract silently lose?

**Source:** graphiti Apache-2.0 `main@993e081a`; Codebase Memory `graphiti`. **Question:** what is the smallest legitimate LLMClient subclass for a provider with only json_object mode — and which structured-output guarantees disappear?

## Minimal-provider subclass of LLMClient
**Path/Symbol:** `graphiti_core/llm_client/groq_client.py:GroqClient` (:48-85); base retry ladder `graphiti_core/llm_client/client.py:_generate_response_with_retry` (:120-131, tenacity `retry_if_exception(is_server_or_retry_error)`).
**Signature:** `__init__(config: LLMConfig | None = None, cache: bool = False)`; `async def _generate_response(messages: list[Message], response_model: type[BaseModel] | None = None, max_tokens: int = 2048, model_size: ModelSize = ModelSize.medium) -> dict[str, typing.Any]`.
**Data Shape:** in: prompt `Message` list (roles user/system/assistant); out: `json.loads(content)` dict; failure: provider `RateLimitError` re-mapped to graphiti `llm_client.errors.RateLimitError`, everything else logged and re-raised raw.

### Decisive source
```python
# groq_client.py :65-85 — role filter, forced json_object, bare parse:
msgs: list[ChatCompletionMessageParam] = []
for m in messages:
    if m.role == 'user':
        msgs.append({'role': 'user', 'content': m.content})
    elif m.role == 'system':
        msgs.append({'role': 'system', 'content': m.content})
try:
    response = await self.client.chat.completions.create(
        model=self.model or DEFAULT_MODEL,
        messages=msgs,
        temperature=self.temperature,
        max_tokens=max_tokens or self.max_tokens,
        response_format={'type': 'json_object'},
    )
    result = response.choices[0].message.content or ''
    return json.loads(result)
except groq.RateLimitError as e:
    raise RateLimitError from e
except Exception as e:
    logger.error(f'Error in generating LLM response: {e}')
    raise
```

**Flow:** constructor defaults `max_tokens` to 2048 when config omits it (`:50-53`) and builds `AsyncGroq(api_key=...)` → callers invoke base `generate_response`, which wraps the override in the inherited tenacity transient-error retry ladder → override forwards ONLY user/system messages → one `chat.completions.create` with `response_format json_object` → `content or ''` parsed by bare `json.loads`.
**Invariant:** `response_model` is ACCEPTED BUT NEVER APPLIED — no schema injection into the prompt, no fence stripping, no repair loop; and any message whose role is neither user nor system (e.g. assistant turns passed as conversation history) is dropped WITHOUT warning. Multi-turn extraction prompts silently degrade to their system+user parts. Retry/transient classification still comes from the base class, not from this file.
**Probe:** offline venv probe RE-EXECUTED pass 11 (verification pass) against REAL GroqClient source with a stubbed `groq` SDK module: call `_generate_response([assistant-msg, user-msg], response_model=object)` → `create` receives roles `['user']` only (assistant turn silently dropped), `response_format == {'type': 'json_object'}`, returned dict `{'a': 1}` from bare `json.loads` — PASS. Import gate verified by source inspection (:31-34 raises actionable ImportError; first stub attempt without `ChatCompletionMessageParam` on the fake module reproduced exactly this gate). No unit test file exists for this client (tests/llm_client has none) — coverage caveat.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "graphiti", query: "GroqClient _generate_response json_object", limit: 10 });
```

## Verdict
Adopt the optional-extra import gate with actionable install hint, default-max-token injection, and the narrow rate-limit-only error mapping. Adapt the role filter: either map assistant turns explicitly or fail loudly — never drop history silently. Omit the bare `json.loads` when schema fidelity matters; route through the generic-client json_schema/json_object ladder (see `generic-client-structured-output`) instead of copying this minimal shape for schema-bearing calls.
