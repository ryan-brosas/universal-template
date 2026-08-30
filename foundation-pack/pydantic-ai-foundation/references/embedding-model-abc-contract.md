<!-- capsule-v2 -->
# Embedding model ABC — prepare_embed normalization hook and the disabled-request guard

## Source / Question
`pydantic_ai_slim/pydantic_ai/embeddings/base.py` @ `main@b3cdbc96` (MIT); Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** Every embedding backend needs the same input normalization (str → [str]) and settings merge before its API call — where does that live so a new backend can't forget it, and how do tests block real network calls uniformly? A porter will re-implement normalization per backend and drift.

## Path / Symbol
`embeddings/base.py` — `EmbeddingModel(ABC)` whole file (:8–116): abstract `embed()` (:58), concrete `prepare_embed()` (:74–92), default `max_input_tokens() → None` (:95), `count_tokens()` raises NotImplementedError (:103).

## Signature
```python
class EmbeddingModel(ABC):
    @abstractmethod
    async def embed(self, inputs: str | Sequence[str], *, input_type: EmbedInputType,
                    settings: EmbeddingSettings | None = None) -> EmbeddingResult: ...
    def prepare_embed(self, inputs, settings=None) -> tuple[list[str], EmbeddingSettings]:
        inputs = [inputs] if isinstance(inputs, str) else list(inputs)
        settings = merge_embedding_settings(self._settings, settings) or {}
        return inputs, settings
```

## Data Shape
`prepare_embed` is the CONCRETE template method subclasses call at the top of their `embed()` implementation — returns normalized inputs (always list[str]) and merged settings (instance defaults ⊕ call overrides, never None). Capability surface beyond embed: `max_input_tokens() -> int | None` defaults to unknown; `count_tokens(text)` deliberately has NO default — unsupported backends must raise NotImplementedError loudly rather than guess.

### Decisive source (:80–81 + test-pinned guard behavior)
```python
"""Prepare the inputs and settings for embedding.

This method normalizes inputs to a list and merges settings.
Subclasses should call this at the start of their `embed()` implementation."""
```
The request-guard contract (`tests/test_embeddings.py::test_openai_embedding_model_blocks_requests_when_disabled` :103 and one per backend): every backend's network entry raises when model requests are disabled by the test harness — enforced UNIFORMLY across openai/cohere/google/bedrock/voyageai (:103–157), with `TestEmbeddingModel` explicitly EXEMPT (:181).

**Flow:** caller → backend.embed → `prepare_embed(inputs, settings)` first line → vendor API call with normalized list → wrap response in EmbeddingResult. Wrapper/Instrumented twins delegate through the same ABC surface; `WrapperEmbeddingModel` forwards, instrumentation wraps spans+metrics around `embed`.

**Invariant:** Normalization+merge happens in exactly ONE place (the base-class template method); backends never see raw str inputs or unmerged settings. Token counting fails loud (NotImplementedError / UserError), never fabricates counts. The disabled-guard is part of the backend contract, not optional hygiene.

**Probe:** `tests/test_embeddings.py` — guard matrix :103–166, exemption :181, `test_hf_hub_unavailable_classifier` (:231), `test_stsb_model_pin_matches_ci` (:268); VCR cassettes under `tests/cassettes/test_embeddings/`.

## Get live surrounding code
**Retrieve:**
```
search_graph --project mnt-hdd-utopia-inspo-pydantic-ai --query 'EmbeddingModel prepare_embed merge_embedding_settings'
```

## Verdict
**Adopt** the template-method normalization hook for any multi-backend client family. **Adopt** the uniform disabled-request guard as a tested backend obligation. **Omit** concrete backends (vendor wrappers).
