<!-- capsule-v2 -->
# Model vs transport split — where does the DIP boundary sit between "answer my calls" and "speak this provider's wire protocol"?

**Source:** pipeshub-ai Apache-2.0 `main@c28d133…`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-pipeshub-ai`. **Question:** How do you let Agent depend on an LLM interface that decorators (retry/caching/fallback-to-second-model) can wrap WITHOUT reaching into transport internals?

## Three single-method Protocols compose into the ABC; TransportModel is deliberately thin
**Path/Symbol:** `backend/python/app/agent_loop_lib/models/base.py:SupportsComplete/SupportsStructuredComplete/SupportsStreaming/Model` (:32 / :46 / :57 / :71) + `models/transport.py:TransportModel`.
**Signature:** `SupportsComplete.complete(messages, tools=None, system=None, model=None, thinking_budget=None, effort=None, system_blocks=None) -> ModelResponse`; `SupportsStructuredComplete.complete_structured(messages, output_schema, system=None, model=None) -> StructuredResponse`; `SupportsStreaming.stream(...) -> AsyncIterator[StreamEvent]`.
**Data Shape:** All `@runtime_checkable` Protocols; `Model(SupportsComplete, SupportsStructuredComplete, SupportsStreaming, ABC)` adds abstract `model_name`. History (module docstring, load-bearing): transports once returned bare Message with usage on a mutable `self.last_usage` side-channel callers read via getattr afterwards — replaced by explicit immutable `ModelResponse(message, usage, stop_reason, model)` / `StructuredResponse(data, usage, model)` envelopes (core/responses.py).

### Decisive source
```python
# Split into three single-method Protocols (Interface Segregation) plus the
# concrete Model ABC that composes all three: most callers only need ONE of
# complete/complete_structured/stream (e.g. Planner/Critic/IntentParser only
# ever call complete_structured) and should depend on exactly that …
class TransportModel(Model):
    """Adapts any LLMTransport … A thin pass-through today … the value is
    structural (DIP): Agent can be handed any Model, including a decorator
    that wraps a TransportModel with retry/caching/fallback behavior,
    without ever importing LLMTransport itself."""
```

**Flow:** Provider transport implements wire dialects (see transport-dialect-layer) → `TransportModel(transport)` adapts it to `Model` → `Agent` holds a `Model`, never an `LLMTransport` → cross-cutting decorators wrap ANY Model transparently → run-cost accumulation lives in `RunUsage.add(request_usage)` (:59–80) as the explicit replacement for reading cumulative counters off a concrete transport instance.
**Invariant:** (1) `Agent` must never import/type-against `LLMTransport` — collapsing the two concerns makes retry/caching/fallback composition impossible without reaching into provider internals. (2) Per-call outcomes are RETURN VALUES (usage/stop_reason/model), never side-channel attributes read after await — the mutable last_usage pattern races under concurrency and forgets to be set. (3) Callers needing one capability depend on exactly that Protocol (runtime_checkable so tests can duck-verify).
**Probe:** No dedicated unit file for models/base.py at this pin — deterministic check: instantiate a duck-typed object with only `complete_structured` and assert `isinstance(x, SupportsStructuredComplete)` passes while full-Model checks fail; envelope behavior pinned indirectly by planner/critic suites (`test_default.py::test_calls_complete_not_complete_structured`) and transport tests under `tests/unit/agent_loop_lib/transport/`.
**Retrieve:**
```bash
codebase-memory-mcp cli search_graph '{"project":"mnt-hdd-utopia-inspo-platforms-pipeshub-ai","query":"SupportsComplete SupportsStructuredComplete TransportModel ModelResponse","detail":"ids","limit":5}'
```

## Verdict
Adopt the three-Protocol decomposition plus explicit response envelopes and the never-side-channel rule; adopt TransportModel as the single adapter point. Adapt parameter surface (thinking_budget/effort/system_blocks) to your providers. Omit nothing — this is pure structure. Coverage caveat: no direct unit suite for the Protocol file; contracts are exercised through planner/critic/transport suites.
