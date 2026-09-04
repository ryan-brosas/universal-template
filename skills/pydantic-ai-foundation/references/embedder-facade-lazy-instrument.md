<!-- capsule-v2 -->
# Embedder facade — defer_model_check, ContextVar override, and read-time instrumentation

## Source / Question
`pydantic_ai_slim/pydantic_ai/embeddings/__init__.py` @ `main@b3cdbc96` (MIT); Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** How does a high-level embedder keep construction cheap (no provider import until first use), allow test-time model overrides without touching instance state other code might capture, and apply instrumentation at the last possible moment? A porter will resolve the provider in `__init__` and bake instrumentation into stored instances.

## Path / Symbol
`embeddings/__init__.py` — `Embedder` dataclass (:142–391): ctor (:177–206), `instrument_all()` (:208–220), `override()` (:227–264), `_get_model()` (:375–391), `infer_embedding_model()` (:83–139), sync twins (:349–373).

## Signature
```python
@dataclass(init=False)
class Embedder:
    _instrument_default: ClassVar[InstrumentationSettings | bool] = False
    def __init__(self, model, *, settings=None, defer_model_check: bool = True,
                 instrument: InstrumentationSettings | bool | None = None):
        self._model = model if defer_model_check else infer_embedding_model(model)
        self._override_model: ContextVar[EmbeddingModel | None] = ContextVar(..., default=None)
    def _get_model(self) -> EmbeddingModel:
        # override wins → else infer NOW → instrument_embedding_model(model_, instrument)
```

## Data Shape
`model` stays a raw string (`'openai:text-embedding-3-small'`) until first use. `instrument=None` means "fall back to the process-wide ClassVar default set via `instrument_all()`"; explicit values win per-embedder. The override is a ContextVar on the INSTANCE — scoped to the async context that entered it, reset in finally.

### Decisive source — resolution + instrumentation ordering (:381–391)
```python
def _get_model(self) -> EmbeddingModel:
    model_: EmbeddingModel
    if some_model := self._override_model.get():
        model_ = some_model
    else:
        model_ = self._model = infer_embedding_model(self.model)   # deferred inference
    instrument = self.instrument
    if instrument is None:
        instrument = self._instrument_default                       # global fallback
    return instrument_embedding_model(model_, instrument)           # wrapped EVERY call
```
And the query/document split: `embed_query(input_type='query')` vs `embed_documents(input_type='document')` — same call path, but `input_type` is forwarded because several providers optimize embeddings differently per role.

**Flow:** construct (string held) → first `embed()` → ContextVar override checked → else lazy `infer_embedding_model` (provider prefix split, gateway normalization, chat-compatible-provider union reused for embeddings; unknown ⇒ UserError) → wrap with instrumentation using resolved settings → merge settings (instance defaults ⊕ call overrides) → delegate. Sync twins run the coroutine via `_utils.run_until_complete`.

**Invariant:** Instrumentation must be applied per-resolution (idempotent wrapper), never persisted onto `self._model` — otherwise a later `instrument_all()` flip or override can't change behavior. Model inference failure should surface at first USE by default (`defer_model_check=True`), keeping imports cheap.

**Probe:** `tests/test_embeddings.py` — `test_embedder_blocks_requests_when_disabled` (:166), `test_test_embedding_model_is_exempt_from_request_guard` (:181), infer matrix :294+; VCR-cassette coverage for OpenAI count_tokens.

## Get live surrounding code
**Retrieve:**
```
search_graph --project mnt-hdd-utopia-inspo-pydantic-ai --query 'Embedder infer_embedding_model instrument_embedding_model'
```

## Verdict
**Adopt** the three-lazy pattern (deferred inference + ContextVar override + read-time instrumentation) for any facade over remote services. **Adopt** query/document input_type as a first-class axis. **Adapt** the provider dispatch ladder to your vendor set. **Omit** individual embedding backends (`bedrock/cohere/google/voyageai/sentence_transformers/openai.py` — thin API wrappers, vendor surface).
