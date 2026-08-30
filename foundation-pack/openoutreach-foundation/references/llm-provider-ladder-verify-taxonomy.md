<!-- capsule-v2 -->
# Provider ladder with typed verification — how do you accept `provider:model` (and barely-any bare names), and which exceptions count as "the operator's key is wrong" vs a bug?

**Source:** OpenOutreach GPL-3.0 `main@c3ac1434118ac5301b193506d1d01e6e313bc622`; Codebase Memory `openoutreach`. **Question:** Where do you draw the line between a credential answer you can report and an in-process bug you must not swallow as one?

## Connected graph-selected seam
**Path/Symbol:** `openoutreach/core/llm.py` — `_PROVIDER_BUILDERS` (:144-152), `_LEGACY_MODEL_PREFIXES` (:158-161), `split_model_id` (:164-180), `build_llm_model` (:197-210), `_ping_model` (:219-224), `verify_llm_credentials` (:227-243).
**Signature:** `split_model_id(ai_model: str) -> tuple[str, str]`; `build_llm_model(ai_model, api_key, api_base="")`; `verify_llm_credentials(ai_model, api_key, api_base="") -> str | None`.
**Data Shape:** model id grammar `"provider:model"`; bare names accepted only for prefixes `gpt|o1|o3 → openai`, `claude → anthropic`, `gemini → google`; seven builder keys incl. `openai_compatible` (requires explicit api_base).

### Decisive source
```python
    try:
        _ping_model(ai_model, api_key, api_base)
        return None
    except (ModelAPIError, UserError, ValueError) as exc:
        return str(exc)
```
And the reason the tuple is exactly that long (:233-235):
```python
#     because the caller reports what it catches here as the operator's credentials
#     being wrong, and sending someone after a key that is fine is worse than a
#     traceback. (`anthropic` 1.0.0 dropping `temperature` read as a rejected key for
#     an afternoon; it was a `TypeError` in our own process.)
```

**Flow:** `split_model_id` partitions on `:`; a bare name falls through the legacy-prefix map or **raises** ("misconfiguration surfaces instead of silently hitting the wrong API") → `build_llm_model` looks up the builder registry; unknown provider raises listing every valid provider → `verify_llm_credentials` (onboarding path) live-pings via `_ping_model` (@retry 3 attempts, exp wait ≤10s, reraise) and converts *only* provider-shaped errors into a string answer.
**Invariant:** The catch list is a closed taxonomy: only what a configuration can cause (`ModelAPIError`, pydantic-ai `UserError`, local `ValueError`) is an "answer"; anything else propagates so a library incompatibility keeps its traceback instead of reading as a rejected key. Bare-name routing stays minimal — groq/mistral/cohere/openai_compatible carry no reliable prefix and must be written `provider:model`.
**Probe:** `tests/test_llm.py:37-50` `test_verify_llm_credentials_does_not_swallow_a_bug` (TypeError re-raised), `:27-34` unusable-model-id-is-an-answer, `:17-24` 401 refusal reported verbatim, `:7-9` unknown-provider raise, `:53-71` `test_every_provider_sdk_is_silenced_at_debug` asserting every `_PROVIDER_BUILDERS` key's SDK logger appears in `core.logging.SILENCED_LOGGERS` (cross-module coupling test — a new provider must arrive silenced).
**Coverage:** same file checks as llm-persistent-loop-runner (no_recorded_issue / metadata_match @ gen 2026-08-25T20:08:16Z).

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "openoutreach", query: "verify_llm_credentials split_model_id provider", limit: 10 });
```

## Verdict
Adopt: prefix-laddered id parsing that raises on ambiguity, a builder registry whose unknown-key error lists the valid set, and the closed exception taxonomy separating credential answers from bugs. Adapt provider keys/SDK imports to your stack; omit the SDK-logger silencing if you have no debug surface — but keep whatever equivalent coupling test forces new providers to register everywhere at once.
