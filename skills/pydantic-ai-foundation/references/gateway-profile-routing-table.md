<!-- capsule-v2 -->
# Gateway profile routing table — how does one provider serve many upstream vendors without losing vendor-specific behavior?

**Source:** pydantic-ai MIT `main@a5b5fb7a247f863599d61dfa9159bc2ebc786255` (Vercel AI Gateway provider); Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** A gateway provider receives `vendor/model` names — where should the vendor-profile lookup live, and what breaks when the table has a gap?

## gateway-profile-routing-table
**Path/Symbol:** `pydantic_ai_slim/pydantic_ai/providers/vercel.py:` `VercelProvider.model_profile` staticmethod (:49–73, table :52–62).
**Signature:** `model_profile(model_name: str) -> ModelProfile | None`; entries are `provider_prefix → profile_fn` callables (`anthropic_model_profile`, `amazon_model_profile`, `cohere_model_profile`, `deepseek_model_profile`, `groq_model_profile`, `mistral_model_profile`, `openai_model_profile`, `google_model_profile`, `grok_model_profile`).
**Data Shape:** model_name convention `<vendor>/<model>`; no-slash ⇒ default `OpenAIModelProfile(json_schema_transformer=OpenAIJsonSchemaTransformer)`; unknown vendor prefix ⇒ `profile=None`.

### Decisive source
```python
provider_to_profile = {
    'bedrock': amazon_model_profile,
    'cohere': cohere_model_profile,
    'deepseek': deepseek_model_profile,
    'groq': groq_model_profile,   # added #7551 — was silently missing
    'vertex': google_model_profile,
    ...
}
if '/' not in model_name:
    return OpenAIModelProfile(json_schema_transformer=OpenAIJsonSchemaTransformer)
provider, model_name = model_name.split('/', 1)
if provider in provider_to_profile:
    profile = provider_to_profile[provider](model_name)   # NOTE: suffix, not full name
# always re-merged with the OpenAI transformer baseline:
return merge_profile(OpenAIModelProfile(json_schema_transformer=OpenAIJsonSchemaTransformer), profile)
```

**Flow:** split-once-on-first-slash → delegate to the VENDOR's own profile function with the SUFFIX → merge the vendor result over a constant OpenAI-transformer baseline so schema-transformer behavior never regresses for unlisted vendors.
**Invariant:** four rules:
1. A missing table row is not an error — it is silent capability loss: `groq/llama-3.3-70b-versatile` ran with generic defaults (e.g. wrong streaming/thinking flags) until #7551. New vendor prefixes must land in the table THE SAME commit that accepts their model names.
2. Delegate to each vendor's OWN profile function; never hand-roll per-vendor logic inside the gateway — the twin fix history (#7551 groq here; #7723 r1-alias inside deepseek's function) shows the two layers are fixed independently.
3. The merge-with-baseline step is what keeps "unknown vendor" safe; keep it AFTER delegation.
4. Pass the model-name SUFFIX to vendor profile functions — they match on bare names (`'r1'`, `'deepseek-r1…'`), not gateway ids.
**Probe:** direct behavioral check EXECUTED this pass in repo `.venv`: `VercelProvider.model_profile('groq/llama-3.3-70b-versatile')` returns a merged dict carrying `groq_always_has_web_search_builtin_tool` / `groq_supports_graded_reasoning_effort` keys (proves the groq row resolved); regression pin `tests/providers/test_vercel.py::test_groq_profile_not_dropped` (:60–68 area).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pydantic-ai", query: "VercelProvider model_profile groq provider_to_profile", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the prefix→delegate→merge-over-baseline pattern for any multi-vendor gateway facade; adapt table contents and the baseline profile to your host's transformer defaults; omit the OpenAI-specific json_schema_transformer if your host has a different universal baseline.
