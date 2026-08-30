<!-- capsule-v2 -->
# Concurrency-limited model wrapper — limiter normalization and shared-pool identity

## Source / Question
`pydantic_ai_slim/pydantic_ai/models/concurrency.py` @ `main@b3cdbc96` (MIT); Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** How does a model-level concurrency gate wrap ALL three request surfaces (request, count_tokens, request_stream) so streaming can't bypass the budget, and how do users share one pool across models? A porter will wrap only `request()` and leak unbounded concurrent streams.

## Path / Symbol
`models/concurrency.py` — `ConcurrencyLimitedModel(WrapperModel)` (:27–111), `limit_model_concurrency()` (:114–142).

## Signature
```python
@dataclass(init=False)
class ConcurrencyLimitedModel(WrapperModel):
    def __init__(self, wrapped: Model | KnownModelName,
                 limiter: int | ConcurrencyLimit | AbstractConcurrencyLimiter): ...
def limit_model_concurrency(model, limiter: AnyConcurrencyLimit) -> Model
```

## Data Shape
`limiter` accepts an int (private unlimited-queue limiter), a `ConcurrencyLimit` (private with backpressure), or a pre-built `AbstractConcurrencyLimiter` (SHARED across every model handed the same instance). Normalization happens in the ctor: instances pass through; scalars go through `ConcurrencyLimiter.from_limit`.

### Decisive source
```python
async def request(self, messages, model_settings, model_request_parameters) -> ModelResponse:
    async with get_concurrency_context(self._limiter, f'model:{self.model_name}'):
        return await self.wrapped.request(messages, model_settings, model_request_parameters)

@asynccontextmanager
async def request_stream(self, messages, model_settings, model_request_parameters, run_context=None):
    async with get_concurrency_context(self._limiter, f'model:{self.model_name}'):
        async with self.wrapped.request_stream(
            messages, model_settings, model_request_parameters, run_context
        ) as response_stream:
            yield response_stream
```
And the None-passthrough helper:
```python
normalized_limiter = normalize_to_limiter(limiter)
if normalized_limiter is None:
    return infer_model(model) if isinstance(model, str) else model
return ConcurrencyLimitedModel(model, normalized_limiter)
```

**Flow:** Every entry point opens `get_concurrency_context(limiter, 'model:{name}')` BEFORE delegating to the wrapped model — including `request_stream`, which holds the slot for the whole stream lifetime (acquired at CM enter, released only when the inner stream CM exits). The `source` string `'model:{model_name}'` is what shows up in waiting-span telemetry. `limit_model_concurrency(None)` returns the model unchanged (no wrapper at all), keeping call sites branch-free.

**Invariant:** A slot must span the ENTIRE streamed response, not just its opening — releasing after the first chunk reintroduces the burst the wrapper exists to prevent. Sharing semantics come from object identity of the limiter, not from name matching.

**Probe:** `tests/test_concurrency.py::TestConcurrencyLimitedModel` (:345) — `test_basic_concurrency_limit` (:348), `test_shared_limiter_limits_across_models` (:410), `test_limit_model_concurrency_helper` (:455); `TestConcurrencyLimitedModelMethods` (:652) covers count_tokens/request_stream paths.

## Get live surrounding code
**Retrieve:**
```
search_graph --project mnt-hdd-utopia-inspo-pydantic-ai --query 'ConcurrencyLimitedModel limit_model_concurrency get_concurrency_context'
```

## Verdict
**Adopt** the all-three-surfaces gating + whole-stream slot hold as THE contract for rate-limiting model calls in a multi-agent host. **Adopt** identity-based pool sharing (`ConcurrencyLimiter(max_running=N, name='pool')` handed to several models). **Adapt** the `source` label format to your telemetry naming. **Omit** the `KnownModelName` string-inference plumbing (provider surface).
