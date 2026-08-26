<!-- capsule-v2 -->
# LLM provider protocol — typed ainvoke with structured output + strict-schema optimizer

**Source:** browser-use MIT `<branch>@<commit>`; Codebase Memory `browser-use`. **Question:** how does an agent talk to 15+ LLM providers through one typed interface and still get reliable structured output?

## Connected graph-selected seam
**Path/Symbol:** `browser_use/llm/base.py`: `BaseChatModel` (Protocol :18) — `provider`/`name`/`model_name` properties, overloaded `ainvoke(messages, output_format: type[T] | None)` returning `ChatInvokeCompletion[T] | ChatInvokeCompletion[str]`, `__get_pydantic_core_schema__` so the Protocol itself is a valid pydantic type; per-provider dirs (`openai/`, `anthropic/`, `google/`, `aws/`, `ollama/`, ... ~15 backends); `llm/schema.py`: `SchemaOptimizer.create_optimized_json_schema` (:12), `_make_strict_compatible` (:187), `create_gemini_optimized_schema` (:206).
**Signature:** every backend implements the same two-mode `ainvoke`: no format → string; `type[T]` → validated T. Serializers per provider (`OpenAIMessageSerializer.serialize_messages`) translate the neutral `BaseMessage`.
**Data Shape:** `ChatInvokeCompletion {completion, usage: ChatInvokeUsage, stop_reason?}` — usage normalized across providers.

### Decisive source
```ts
# strict structured output via OpenAI json_schema:
response_format = {'name': 'agent_output', 'strict': True,
  'schema': SchemaOptimizer.create_optimized_json_schema(output_format, ...)}
# reasoning models: temperature/frequency_penalty are invalid -> popped
if any(m in self.model for m in self.reasoning_models):
    model_params['reasoning_effort'] = self.reasoning_effort
    model_params.pop('temperature'); model_params.pop('frequency_penalty')
# empty-choices guard with proxy hint:
raise ModelProviderError('missing choices... ensure base_url proxy implements /v1/chat/completions', status_code=502)
# reasoning models can burn budget on hidden reasoning: finish_reason='length' + content=None
```

**Flow:** agent calls `ainvoke(messages, SomeModel)` → provider serializer converts messages → params assembled (None-valued skipped) → reasoning-model param fixups → either plain completion or strict JSON-schema response_format → parse+validate into T → normalized usage returned. SchemaOptimizer strips pydantic noise (defaults, minItems, forbidden fields, forces additionalProperties:false) to survive each vendor's strict mode.
**Invariant:** one neutral message type in, one typed result out (usage always populated); schema quirks fixed at ONE place (the optimizer), not per call site; provider failures raise typed errors with actionable hints.
**Probe:** `tests/llm/` tests (schema optimizer makes strict-compatible schemas; usage extraction per provider; reasoning-model param stripping).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "browser-use", query: "BaseChatModel ainvoke SchemaOptimizer strict json_schema ChatInvokeUsage", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the Protocol-based provider interface with two-mode ainvoke + a central strict-schema optimizer; adapt serializers per vendor.
