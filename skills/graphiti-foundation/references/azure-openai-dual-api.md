<!-- capsule-v2 -->
# Azure OpenAI client — dual-API split by reasoning support, shape-adaptive parsing

**Source:** graphiti MIT `main@993e081a`; Codebase Memory `mnt-hdd-utopia-inspo-memory-graphiti`. **Question:** one Azure client must serve reasoning models (o1/o3/gpt-5) and regular chat models — how do request construction AND response parsing both branch without duplicating the retry/cache machinery?

## Azure OpenAI dual-API client
**Path/Symbol:** `graphiti_core/llm_client/azure_openai_client.py`: `AzureOpenAILLMClient(BaseOpenAIClient)` (:31-168); `_create_structured_completion` (:57-105), `_create_completion` (:107-129), `_handle_structured_response` (:131-162), `_supports_reasoning_features` (:164-168); class constant `MAX_RETRIES = 2` (:38).
**Signature:** accepts `AsyncAzureOpenAI | AsyncOpenAI` (Azure v1 compat endpoint) — the base class supplies retry/cache/preamble; subclasses implement only completion + parse.
**Data Shape:** reasoning branch uses Responses API (`responses.parse` with `input`, `max_output_tokens`, `text_format`, `reasoning: {'effort':...}`, `text: {'verbosity':...}`); regular branch uses `beta.chat.completions.parse` with `response_format=response_model`.

### Decisive source
```python
# MODEL gate decides the API — prefix match, not capability probe:
reasoning_prefixes = ('o1', 'o3', 'gpt-5')
return model.startswith(reasoning_prefixes)

# Regular models on Azure v1: responses.parse is NOT fully supported there,
# so structured output goes through beta.chat.completions.parse:
request_kwargs = {'model': model, 'messages': messages, 'max_tokens': max_tokens,
                  'response_format': response_model}
if temperature is not None:
    request_kwargs['temperature'] = temperature
return await self.client.beta.chat.completions.parse(**request_kwargs)

# PARSING branches on RESPONSE SHAPE (hasattr), not on the request path taken:
if hasattr(response, 'choices') and response.choices:
    message = response.choices[0].message
    if hasattr(message, 'parsed') and message.parsed:
        return message.parsed.model_dump()
    elif hasattr(message, 'refusal') and message.refusal:
        raise RefusalError(message.refusal)
elif hasattr(response, 'output_text'):            # Responses API shape
    response_object = response.output_text
    if response_object:
        return json.loads(response_object)
```

**Flow:** `_supports_reasoning_features(model)` → build kwargs for the matching API (reasoning: effort resolved via `_resolve_reasoning_effort`; temperature suppressed for reasoning models in plain completions :125) → parse by response SHAPE with refusal checks on both paths → unknown shape raises. Cache disabled at this level (`cache=False` passed to super).
**Invariant:** (1) the model-prefix gate and the response-shape dispatch are INDEPENDENT — never infer the parse path from which request you "think" you sent (defensive against proxies/gateways rewriting responses); (2) Azure's v1 endpoint does not fully support `responses.parse` for non-reasoning models — forcing it there is a real-world silent failure; (3) refusals raise typed `RefusalError` (feeds the client-layer retry taxonomy) rather than returning empty dicts.
**Probe:** anchored at repo root. Battery: `grep -c "hasattr(response, 'output_text')" graphiti_core/llm_client/azure_openai_client.py` → 1; `grep -c 'beta.chat.completions.parse' graphiti_core/llm_client/azure_openai_client.py` → 4; `grep -c 'MAX_RETRIES: ClassVar\[int\] = 2' graphiti_core/llm_client/azure_openai_client.py` → 1. Direct-test coverage caveat: no dedicated unit suite for this file at pin (upstream tests target openai_generic/base clients); contract source-verified.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-memory-graphiti", query: "AzureOpenAILLMClient responses.parse text_format RefusalError", limit: 6, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the twin split (model-gated request building, shape-gated parsing) plus typed refusal errors whenever one client spans OpenAI reasoning and chat APIs; adapt prefixes as new model families land; omit the Azure-v1 fallback if you only hit first-party endpoints. Coverage caveat stated above.
