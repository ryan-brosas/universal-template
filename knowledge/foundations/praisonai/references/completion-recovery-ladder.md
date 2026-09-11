<!-- capsule-v2 -->
# Completion recovery ladder — how does one failed LLM call become exactly one recovery action without unbounded recursion?

**Source:** praisonai MIT `main@d82364ec23a83fd9a6e2e849a5285442b4734ca3`; Codebase Memory `praisonai`. **Question:** When the provider call raises, which single recovery action runs, what bounds its recursion, and how is a temporary model swap prevented from leaking into later calls?

## ChatMixin._chat_completion error path
**Path/Symbol:** `src/praisonai-agents/praisonaiagents/agent/chat_mixin.py:ChatMixin._chat_completion` (lines 1747–2142; error ladder ≈ 2005–2140).
**Signature:** `_chat_completion(self, messages, temperature=None, tools=None, stream=None, reasoning_steps=False, task_name=None, task_description=None, task_id=None, response_format=None, _retry_depth=0, _fallback_index=0)`.
**Data Shape:** inputs: message list (mutated in place by compaction), `_retry_depth`/`_fallback_index` recursion counters; output: provider response object; failure: raises `BudgetExceededError`, `ToolExecutionError` (passthrough), or `LLMError` carrying `error_category` + user remediation context.

### Decisive source
```python
except BudgetExceededError:
    raise
except ToolExecutionError:
    raise
except Exception as e:
    ...
    classification = classify_llm_error(
        e, provider=provider, model=model_name,
        prompt_tokens=prompt_tokens, context_length=context_length,
        retry_depth=_retry_depth,
    )
    if classification.should_compress_context and self.context_manager:
        target = int(model_limit * 0.7)  # 70% of limit for safety
        truncated_messages = self.context_manager.emergency_truncate(messages, target)
        if _retry_depth < self._max_retry_depth():
            return self._chat_completion(truncated_messages, ..., _retry_depth=_retry_depth + 1, _fallback_index=_fallback_index)
    elif classification.should_fallback_model:
        next_model = self._get_next_fallback_model(_fallback_index)
        if next_model:
            original_llm = self.llm
            original_dispatcher = getattr(self, '_unified_dispatcher', None)
            try:
                self.llm = next_model
                self._unified_dispatcher = None  # Force recreation with new model
                return self._chat_completion(messages, ..., _retry_depth=_retry_depth + 1, _fallback_index=_fallback_index + 1)
            finally:
                self.llm = original_llm
                self._unified_dispatcher = original_dispatcher  # Restore original dispatcher
    elif classification.is_retryable and classification.backoff_seconds > 0:
        if _retry_depth < self._max_retry_depth():
            time.sleep(classification.backoff_seconds)
            return self._chat_completion(messages, ..., _retry_depth=_retry_depth + 1, ...)
    error = LLMError(str(e), model_name=model_name, agent_id=self.name,
                     is_retryable=classification.is_retryable,
                     context={"session_id": session_id, "error_category": classification.error_category, "user_message": user_message})
    raise error from e
```

**Flow:** passthrough re-raise for BudgetExceeded/ToolExecution → classify (provider guessed from model name; prompt tokens estimated) → priority-ordered actions: (1) compress context to 70% of model limit and retry in place, (2) walk the fallback-model chain with a temporary `self.llm` override plus dispatcher-cache invalidation, (3) sleep `backoff_seconds` and retry — each guarded by `_retry_depth < _max_retry_depth()` → exhausted actions wrap in `LLMError` with category + remediation text and call `on_error`.
**Invariant:** every recursive retry increments `_retry_depth` (and `_fallback_index` when advancing the chain); the temporary fallback model and dispatcher cache are restored in `finally` so the agent's configured primary model survives a failed fallback; BudgetExceededError and ToolExecutionError are never reclassified as retryable LLM faults.
**Probe:** `src/praisonai-agents/tests/unit/llm/test_error_classifier.py:196–202` pins the vocabulary this ladder depends on — a budget-exhaustion exception classifies as `ErrorCategory.PERMANENT` with `should_retry(category) is False`; lines 208–213 pin Retry-After header extraction (`{"retry-after": "42"} → 42.0`) feeding `classification.backoff_seconds`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "praisonai", query: "_chat_completion retry fallback classify", name_pattern: "^classify_llm_error$|^_get_next_fallback_model$", limit: 10 });
```

## Verdict
Adopt the classify→single-action ladder with depth-bounded recursion and `finally`-restored model swap; adopt passthrough re-raise for non-LLM fault classes. Adapt provider guessing (name-substring heuristic), litellm-based cost calculation, and the `_unified_dispatcher` invalidation hook to your host. Omit the concrete fallback-chain configuration surface until you read `_get_next_fallback_model` (chat_mixin.py:1619–1632) against your own model registry. Coverage: chat_mixin.py has no recorded index issue; the classifier contract is directly tested, the ladder wiring itself is not — verify by trace before porting.
