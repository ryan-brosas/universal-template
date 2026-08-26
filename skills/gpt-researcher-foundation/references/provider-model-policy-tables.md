<!-- capsule-v2 -->
# Provider model policy tables — which capability lists gate reasoning_effort, temperature, and streamed usage reporting?

**Source:** gpt-researcher Apache-2.0 `main@5d84d2f5553e70a2765a8ff3a0d2672d60437ce8`; Codebase Memory `gpt-researcher`. **Question:** Where are the per-model parameter policies declared, and what must a porter re-derive when adding a new model?

## Three tables in llm_provider/generic/base.py
**Path/Symbol:** `gpt_researcher/llm_provider/generic/base.py:13-90` — `_SUPPORTED_PROVIDERS` (26 providers), `NO_SUPPORT_TEMPERATURE_MODELS`, `SUPPORT_REASONING_EFFORT_MODELS`, `ReasoningEfforts` enum (high/medium/low).
**Signature:** plain module-level `list[str]` / `set[str]`; membership tested by exact string.
**Data Shape:** NO_SUPPORT contains dated variants too (`o1-mini-2024-09-12`, `claude-opus-4-7`, `gpt-5.4-nano`…). SUPPORT_REASONING_EFFORT is the OpenAI reasoning subset only. `GenericLLMProvider.from_provider` maps each provider name to its LangChain chat class; `_check_pkg` auto-pip-installs missing provider packages.

### Decisive source
```python
if model in SUPPORT_REASONING_EFFORT_MODELS:
    provider_kwargs['reasoning_effort'] = reasoning_effort
...
# openai arm of from_provider:
kwargs.setdefault("stream_usage", True)
llm = ChatOpenAI(**kwargs)
```

**Flow:** config parses `SMART_LLM = "provider:model"` (`config.py parse_llm` asserts provider ∈ set) → every call site checks these tables before building kwargs → `get_chat_response` captures `usage_metadata`/`response_metadata` off the returned message (reset before each call) → costs.py consumes them.
**Invariant:** `stream_usage=True` is what makes cost tracking use REAL tokens on streamed calls instead of tiktoken estimates over serialized dicts (which overcount input and miss reasoning tokens). A porter dropping that kwarg silently degrades the whole cost ledger.
**Probe:** battery P03a-d GREEN (`NO_SUPPORT_TEMPERATURE_MODELS = [` ×1; `"gpt-5",` and `"claude-opus-4-7",` pinned; `kwargs.setdefault("stream_usage", True)` ×1).
**Coverage caveat:** table contents are point-in-time vendor policy; treat as data to refresh, not logic.
