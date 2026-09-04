<!-- capsule-v2 -->
# Provider factories — capability-based client routing with fatal reranker rule

**Source:** graphiti MIT `main@401c59a`; Codebase Memory `graphiti`. **Question:** how do you route one YAML config across optional provider deps to build LLM/embedder/cross-encoder clients, and which failures must be fatal vs degraded?

## Connected graph-selected seam
**Path/Symbol:** `mcp_server/src/services/factories.py`: `is_non_openai_provider` (:94), `reasoning_effort_for_model` (:111), `LLMClientFactory.create` (:129), `EmbedderFactory.create` (:305), `CrossEncoderFactory.create` (:422), `_reranker_for_provider` (:455), `DatabaseDriverFactory.create_config` (:522).
**Signature:** `is_non_openai_provider(base_url: str | None) -> bool`; `reasoning_effort_for_model(model: str) -> str | None`; `CrossEncoderFactory.create(llm_config, embedder_config) -> CrossEncoderClient`; `DatabaseDriverFactory.create_config(config) -> dict` (returns a config dict, not a driver instance).
**Data Shape:** module-level try-imports set HAS_* flags per optional dependency; every factory branches on a lowercase `provider` string via structural `match`; each provider block validates its own sub-config exists before touching keys.

### Decisive source
```python
# Client choice is BASE-URL-derived: official endpoint → Responses API client,
# any other host (Ollama/vLLM/LM Studio) → generic Chat Completions client.
openai_domains = ['api.openai.com', 'openai.azure.com']
return not any(domain in base_url for domain in openai_domains)
...
def reasoning_effort_for_model(model):
    if not model.startswith(('o1', 'o3', 'gpt-5')): return None
    return 'none' if model.startswith('gpt-5.5') else 'minimal'
# CrossEncoderFactory docstring: "Reranker setup errors must remain FATAL rather
# than silently restoring the OpenAIRerankerClient default" (needs an OpenAI key).
```

**Flow:** config → LLM/embedder factory failures are caught and logged in `GraphitiService.initialize` (server degrades: extraction/search "limited") → cross-encoder creation is NOT wrapped; failure propagates and kills startup → reranker resolution ladder: LLM provider native reranker → embedder provider native → local BGE model (warns it downloads ~2.3 GB on first run; ImportError becomes an actionable multi-option ValueError) → DB config resolved with env-var overrides (`NEO4J_URI`, `FALKORDB_URI`…) layered over YAML for CI.
**Invariant:** degradation is a deliberate two-tier policy — missing LLM/embedder = warn-and-continue, missing/failed RERANKER = fatal, because core's silent default would need an OpenAI key the deployment just proved it doesn't have; reasoning models get an effort parameter while non-reasoning models must NOT receive one; Azure base_urls are normalized to end with `/openai/v1/`.
**Probe:** `mcp_server/tests/test_factories.py::TestLLMClientFactoryRouting::test_ollama_uses_generic_client`, `TestReasoningEffortForModel::test_effort_selection`, `mcp_server/tests/test_cross_encoder_factory.py::test_graphiti_service_does_not_swallow_reranker_configuration_error`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase-memory.search_graph({ project: "graphiti", query: "LLMClientFactory CrossEncoderFactory is_non_openai_provider reasoning_effort_for_model", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt capability-laddered provider selection (primary → secondary → local fallback with actionable error) and the tiered fatality rule for optional components whose defaults differ from the deployment's assumptions. Adapt domain lists (`openai_domains`, model prefixes). Omit the Azure v1 URL hack if your SDK handles deployment endpoints natively.
