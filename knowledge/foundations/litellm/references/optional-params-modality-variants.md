<!-- capsule-v2 -->
# Optional-params modality variants — embeddings, image-gen, transcription validation twins

**Source:** litellm MIT `litellm_internal_staging@f005afa1460385a218be8ef1fdfa49998bf93523`; Codebase Memory `litellm`. **Question:** How do the non-completion modalities validate and map OpenAI-style params, and where do they diverge from the chat-completion ladder?

## Three per-modality validators in utils.py
**Path/Symbol:** `litellm/utils.py` — `get_optional_params_transcription` (:3011-3097), `get_optional_params_image_gen` (:3117-3239), `get_optional_params_embeddings` (:3242-3341+).
**Signature:** e.g. `get_optional_params_embeddings(model: str, user=None, encoding_format=None, dimensions=None, custom_llm_provider="", drop_params=None, additional_drop_params=None, allowed_openai_params=None, **kwargs)`.
**Data Shape:** each rebuilds `passed_params = locals()`, pops control kwargs, computes `non_default_params` against a modality-specific default table, then returns a mapped `optional_params` dict.

### Decisive source
```python
# utils.py:3310-3320 — embeddings: restore provider-only extras without duplicating mapped values
# Provider-only params (e.g. Cohere input_type) are not in
# OPENAI_EMBEDDING_PARAMS, so embedding_pre_process drops them from
# non_default_params before map_openai_params. Restore only those extras
# from passed_params — skip OPENAI_EMBEDDING_PARAMS to avoid duplicating
# values already mapped (e.g. dimensions -> output_dimension).
if supported_params:
    for param in supported_params:
        if param in OPENAI_EMBEDDING_PARAMS:
            continue
        if param in passed_params and passed_params[param] is not None and param not in optional_params:
            optional_params[param] = passed_params[param]
```
```python
# utils.py:3210-3221 — image-gen: hardcoded vertex mapping when no provider config applies
elif custom_llm_provider == "vertex_ai":
    supported_params = ["n", "size"]
    _check_valid_arg(supported_params=supported_params)
    if n is not None:
        optional_params["sampleCount"] = int(n)
    if size is not None:
        optional_params["aspectRatio"] = _map_openai_size_to_vertex_ai_aspect_ratio(size)
```

**Flow:** transcription: openai/azure pass non-default params straight through; groq uses STT-specific get/map pair; any other provider with a registered `BaseAudioTranscriptionConfig` gets config-driven validate→map; ends with shared `add_provider_specific_params_to_optional_params`. Image-gen: an explicitly-passed `provider_config` wins; else openai/azure/openai-compatible pass through; bedrock resolves its config class FROM THE MODEL STRING (`BedrockImageGeneration.get_config_class`); vertex has the hardcoded n/size branch; finally None/empty-dict/list values are scrubbed so empty payloads never ship. Embeddings: enum providers resolve `BaseEmbeddingConfig` (validate + map + provider-only restore loop); plain "openai" rejects `dimensions` for models without "text-embedding-3" unless dropped/allowed; triton and legacy branches follow.
**Invariant:** All three keep the family contract from the chat ladder — only non-default params are validated, `drop_params` (global or per-call) silently drops unsupported keys, otherwise `UnsupportedParamsError(status_code=500)` is raised and later forced to 400 by the subclass constructor. Each modality owns its own default table and provider-config lookup; nothing is inherited from chat.
**Probe:** Executed live at the pin: `tests/test_litellm/test_openai_embedding_encoding_format_default.py` + `tests/test_litellm/llms/vertex_ai/audio_transcription/test_vertex_ai_audio_transcription_transformation.py::TestProviderRouting` → 17 passed (encoding-format env default/explicit/env-none semantics; transcription param mapping/rejection). Runner blocks recorded: `tests/test_litellm/test_utils.py` collection ImportError (`backoff` missing via litellm.proxy.utils import chain) and `tests/local_testing/test_get_optional_params_embeddings.py` ModuleNotFoundError (`vcr`) — upstream tests exist but cannot run in this environment.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "litellm",
  query: "get_optional_params embedding image transcription function",
  fields: ["lines", "signature"], limit: 15 });
// → rank-1: get_optional_params_transcription (utils.py 3011-3097);
//   rank-2: get_optional_params_image_gen (utils.py 3117-3239); direct tests surfaced alongside
```

## Verdict
Adopt the per-modality validator pattern: own default table → provider-config-first resolution with openai pass-through → drop-or-raise ladder → post-scrub of empty values; plus the embeddings provider-only-param restore that skips already-mapped names. Adapt vendor mappings (vertex aspect-ratio table, bedrock model-keyed config registry) to your provider set. Omit modalities you don't serve rather than generalizing one validator for all. Coverage caveat: runner blocks above are environmental (`vcr`, `backoff` absent), not source gaps; all cited paths no_recorded_issue full mode.
