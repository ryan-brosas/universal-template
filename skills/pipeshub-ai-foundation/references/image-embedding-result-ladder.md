<!-- capsule-v2 -->
|# ImageEmbeddingResult ladder — how does a provider report per-image outcomes so indexing never silently drops an image?

**Source:** pipeshub-ai Apache-2.0 `main@c28d133…`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-pipeshub-ai`. **Question:** What is the exact contract between a multimodal embedding provider and its caller (`VectorStore`), and who owns failure semantics?

## Result-object interface: providers never raise, every input index owes exactly one result
**Path/Symbol:** `backend/python/app/services/embeddings/multimodal/interface.py` (whole file L1–78): dataclass `ImageEmbeddingResult` :21–29, ABC `IMultimodalEmbeddingProvider` :32–78 (`embed_images` :45–48, `normalize` :50–62, `supports_multimodal` :64–72, `provider_name` :74–78).
**Signature:** `async def embed_images(self, image_base64s: list[str]) -> list[ImageEmbeddingResult]`; `async def normalize(self, image_ref: str) -> str | None`; `def supports_multimodal(self) -> bool` (default True); `provider_name` abstract property.
**Data Shape:** `ImageEmbeddingResult(index: int, embedding: list[float] | None = None, error: str | None = None)` — `index` is the position in the CALLER's input list (not batch offset), so callers zip straight back to source chunks even when providers batch/reorder internally.

### Decisive source
```python
@dataclass
class ImageEmbeddingResult:
    """Result of embedding a single image, keyed by its position in the
    input list so callers can zip results back to their source chunks even
    when some images fail or are skipped (e.g. oversized, invalid base64).
    """
    index: int
    embedding: list[float] | None = None
    error: str | None = None

class IMultimodalEmbeddingProvider(ABC):
    # docstring: "...must always return a result for every input index —
    # either an embedding or an error — so embed_images never silently
    # drops entries."
    _normalize_fn: Callable[[str], Any] | None = None   # injected, sync or async

    async def normalize(self, image_ref: str) -> str | None:
        fn = self._normalize_fn or normalize_image_to_base64
        result = fn(image_ref)
        if inspect.isawaitable(result):      # sync/async bridge lives HERE,
            result = await result            # not in each provider
        return result
```

**Flow:** `VectorStore._process_image_embeddings` builds `MultimodalProviderConfig`, calls `MultimodalEmbeddingFactory.create(config)` (None ⇒ unsupported), gates on `supports_multimodal()` (Ollama overrides to False), then awaits `provider.embed_images(base64s)` and hands the result list to `_build_image_points` — the SINGLE place that decides what "failed to embed" means for indexing. The interface deliberately knows nothing about `VectorPoint`/block metadata/page_content.
**Invariant:** `embed_images` NEVER raises to its caller and returns `len(image_base64s)` results, order-correlated by `index`. Normalisation injection must survive both sync and async callables (the awaitable bridge is the base class's job — reimplementing it per provider is how the sync-default path gets dropped).
**Probe:** `backend/python/tests/unit/services/embeddings/multimodal/test_jina_provider.py::TestJinaMultimodalProvider::test_batch_failure_returns_error_results` (:31) — a `RuntimeError` from the HTTP client yields `results[0].embedding is None` with NO exception escaping `embed_images`.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-pipeshub-ai", query: "IMultimodalEmbeddingProvider embed_images", limit: 10 });
```

## Verdict
Adopt the result-object contract (index-keyed, never-raise, one-result-per-input) and the base-class sync/async normalisation bridge; adapt `_normalize_fn` injection to your host's test-patching conventions (PipesHub binds `VectorStore._normalize_image_to_base64` here so legacy patches keep working); omit the specific provider set. Direct-test caveat: only the Jina provider ships a dedicated unit suite at this pin; the other providers are pinned by shared-helper tests + the consumer contract.
