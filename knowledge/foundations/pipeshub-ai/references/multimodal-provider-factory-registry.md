<!-- capsule-v2 -->
|# MultimodalEmbeddingFactory registry — how do you add an image-capable embedding provider without touching the caller?

**Source:** pipeshub-ai Apache-2.0 `main@c28d133…`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-pipeshub-ai`. **Question:** How is provider selection dispatched so `VectorStore` stays closed to modification, and what does the config carry?

## Dict-of-builders keyed by EmbeddingProvider value; unknown provider ⇒ None, never raise
**Path/Symbol:** `backend/python/app/services/embeddings/multimodal/factory.py` (whole file L1–100: `_OPENAI_COMPAT_STYLE_PROVIDERS` :29–32, `_build_openai_compat` :35–45, `_PROVIDER_BUILDERS` :51–91, `MultimodalEmbeddingFactory.create` :97–100); config `config.py` (whole file L1–37, `MultimodalProviderConfig` :13–37).
**Signature:** `@staticmethod create(config: MultimodalProviderConfig) -> IMultimodalEmbeddingProvider | None`.
**Data Shape:** `MultimodalProviderConfig(provider: str | None, api_key, model_name, region_name, aws_access_key_id, aws_secret_access_key, base_url, embedding_size: int | None, dense_embeddings: Any, normalize_fn: Callable | None, logger)` — a plain dataclass so provider classes depend on ~11 fields instead of a whole `VectorStore`.

### Decisive source
```python
_OPENAI_COMPAT_STYLE_PROVIDERS = {
    EmbeddingProvider.OPENAI_COMPATIBLE.value,
    EmbeddingProvider.LM_STUDIO.value,          # same wire shape, different log label
}
_PROVIDER_BUILDERS: dict[str, Callable[[MultimodalProviderConfig], IMultimodalEmbeddingProvider]] = {
    EmbeddingProvider.COHERE.value: lambda config: CohereMultimodalProvider(...),
    EmbeddingProvider.VOYAGE.value: lambda config: VoyageMultimodalProvider(
        dense_embeddings=config.dense_embeddings, ...),     # LangChain delegation
    EmbeddingProvider.AWS_BEDROCK.value: lambda config: BedrockMultimodalProvider(
        ..., embedding_size=config.embedding_size, ...),     # collection-dim aware
    ...
    **{label: _build_openai_compat(label)
       for label in _OPENAI_COMPAT_STYLE_PROVIDERS},         # label-carrying twins
}

@staticmethod
def create(config) -> IMultimodalEmbeddingProvider | None:
    builder = _PROVIDER_BUILDERS.get(config.provider)
    return builder(config) if builder else None     # None => caller logs "unsupported"
```

**Flow:** `VectorStore._multimodal_provider_config()` (:733–753) snapshots its state into the dataclass (binding `normalize_fn=self._normalize_image_to_base64`) → `create()` looks up ONE builder → constructor receives only the fields it declared. Adding a provider = new `<provider>_provider.py` + one registry entry; no caller change (Open/Closed).
**Invariant:** `create` returns None (does NOT raise) for unknown/unconfigured providers — the caller treats None as "no native path, VLM-description fallback applies". Two providers sharing the OpenAI-compatible wire shape MUST be separate registry keys mapping to separately-labelled instances of one class (the label exists for logs, not dispatch).
**Probe:** No dedicated unit suite at this pin (coverage caveat). Deterministic pins: `grep -cF '_PROVIDER_BUILDERS' backend/python/app/services/embeddings/multimodal/factory.py` ≥ 2 and `grep -c 'return builder(config) if builder else None' <same>` == 1; consumer wiring `grep -cF 'MultimodalEmbeddingFactory.create' backend/python/app/modules/transformers/vectorstore.py` == 1 (:816).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-pipeshub-ai", query: "MultimodalEmbeddingFactory create MultimodalProviderConfig", limit: 10 });
```

## Verdict
Adopt the registry-of-lambdas + None-for-unknown dispatch and the narrow-config-dataclass boundary; adapt the key vocabulary (`EmbeddingProvider` enum values) to your host; omit PipesHub's specific provider roster. Coverage caveat: factory/config have no direct upstream specs — the contract is pinned via the consumer (`_process_image_embeddings` guards `provider is None or not provider.supports_multimodal()`).
