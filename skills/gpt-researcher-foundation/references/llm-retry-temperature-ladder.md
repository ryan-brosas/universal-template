<!-- capsule-v2 -->
# LLM retry + temperature ladder — when does a failed completion retry, and which models must never see temperature?

**Source:** gpt-researcher Apache-2.0 `main@5d84d2f5553e70a2765a8ff3a0d2672d60437ce8`; Codebase Memory `gpt-researcher`. **Question:** How do I port the single choke-point that every LLM call flows through, with its retry policy and per-model parameter suppression intact?

## create_chat_completion guard chain
**Path/Symbol:** `gpt_researcher/utils/llm.py:41-152` (`create_chat_completion`).
**Signature:** `async def create_chat_completion(messages, model=None, temperature=0.4, max_tokens=4000, llm_provider=None, stream=False, websocket=None, llm_kwargs=None, cost_callback=None, reasoning_effort=ReasoningEfforts.Medium.value, **kwargs) -> str`
**Data Shape:** Returns response text; raises `RuntimeError` chained from `last_exception` after exhausting attempts. `model=None` raises immediately; `max_tokens > 200_000` raises with an env-var-typo hint (sanity ceiling — upstream enforces real limits).

### Decisive source
```python
max_attempts = 1 if (stream and websocket is not None) else 10
for attempt in range(1, max_attempts + 1):
    try:
        response = await provider.get_chat_response(messages, stream, websocket, **kwargs)
    except Exception as exc:
        last_exception = exc
        if attempt < max_attempts:
            await asyncio.sleep(min(2 ** (attempt - 1), 8)); continue
        break
    if not response:
        ... # empty response counts as failure and retries on the same ladder
    if model not in NO_SUPPORT_TEMPERATURE_MODELS:
        provider_kwargs['temperature'] = temperature
    else:
        provider_kwargs['temperature'] = None
```

**Flow:** validate → build provider kwargs (reasoning_effort only for SUPPORT_REASONING_EFFORT_MODELS; temperature suppressed for NO_SUPPORT list: o1/o3/o3-mini/o4-mini, whole GPT-5 family incl. 5.4/5.5 variants, Claude 4.x sonnet/opus/haiku) → OPENAI_BASE_URL honored → attempt loop with exponential backoff capped at 8s → cost callback fires ONCE on success.
**Invariant:** streamed-with-websocket calls get exactly ONE attempt (retrying mid-stream would duplicate already-delivered chunks); empty responses are failures too; temperature must be `None`, not omitted, for listed models.
**Probe:** `tests/test_llm_max_tokens.py` pins both max_tokens guards; battery P02a-c GREEN (`max_attempts = 1 if (stream and websocket is not None) else 10` ×1; `min(2 ** (attempt - 1), 8)` ×2).
