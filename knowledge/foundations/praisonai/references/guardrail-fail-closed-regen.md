<!-- capsule-v2 -->
# Guardrail regen + fail-closed judge — how does a guardrail retry regenerate with feedback while its LLM judge fails closed on ambiguity?

**Source:** praisonai MIT `main@d82364ec23a83fd9a6e2e849a5285442b4734ca3`; Codebase Memory `praisonai`. **Question:** When an LLM-judged guardrail rejects a response, how is the regeneration bounded and informed by the validator's error — and how does the judge itself treat replies that are neither a clean PASS nor a FAIL?

## Agent._apply_guardrail_with_retry + LLMGuardrail fail-closed branches
**Path/Symbol:** `src/praisonai-agents/praisonaiagents/agent/agent.py:Agent._apply_guardrail_with_retry` (lines 6640–6691; default `max_guardrail_retries = 3` at line 1071). Judge: `praisonaiagents/guardrails/llm_guardrail.py:LLMGuardrail` — `__call__` (lines 75–148) and `_llm_validate` (lines 198–270).
**Signature:** `_apply_guardrail_with_retry(self, response_text, prompt, temperature=1.0, tools=None, task_name=None, task_description=None, task_id=None)` → validated result or raised `Exception`. `LLMGuardrail(description, llm)` → `(is_valid: bool, result_or_reason)`.

### Decisive source
```python
# agent.py — bounded regeneration carrying the validator's error
while retry_count <= self.max_guardrail_retries:
    success, result, error = self._validate_with_guardrail(current_response)
    if success:
        return result
    if retry_count >= self.max_guardrail_retries:
        raise Exception(f"Agent {self.name} response failed guardrail validation after "
                        f"{self.max_guardrail_retries} retries. Last error: {error}")
    retry_count += 1
    execution_config = getattr(self, '_execution_config', None)
    if execution_config is not None:
        total_delay = BackoffPolicy.delay(retry_count, execution_config.retry_initial_delay,
                                          execution_config.retry_backoff_factor, execution_config.retry_jitter)
    else:
        total_delay = 1.0 * (2.0 ** (retry_count - 1))   # plain exponential fallback
    time.sleep(total_delay)
    retry_prompt = f"{prompt}\n\nNote: Previous response failed validation due to: {error}. Please provide an improved response."
    response = self._chat_completion([{"role": "user", "content": retry_prompt}], temperature, tools, ...)
```

```python
# llm_guardrail.py — the judge fails closed in FOUR places
if self.llm is None:
    return False, "Guardrail validation unavailable: no LLM configured"      # __call__
...
if response.upper().startswith("PASS"):
    return True, task_output
elif response.upper().startswith("FAIL"):
    reason = response[5:].strip(": ")
    return False, f"Guardrail validation failed: {reason}"
else:
    # Unclear response - fail closed, matching _llm_validate() and the
    # class's documented "fail-closed by default" contract.
    self.logger.warning(f"Unclear guardrail response: {response}")
    return False, f"Guardrail validation unclear: {response}"
except Exception as e:
    return False, f"Guardrail validation error: {str(e)}"                    # errors block too
```

**Flow:** validate → pass returns immediately → fail with retries left: sleep a backoff delay (ExecutionConfig `BackoffPolicy.delay` when configured, plain exponential otherwise), then regenerate through the normal completion path with a prompt that APPENDS the validator's exact error text ("Previous response failed validation due to: {error}") so the model sees what to fix → fail after the last retry raises with the last error. The judge itself accepts only a reply starting with "PASS" (case-insensitive); "FAIL: reason" extracts the reason; *anything else* — fenced code blocks around PASS, refusals, rambles — validates False, and so do a missing LLM, an unsupported LLM type, and any exception during validation. Both entry points (`__call__` for task outputs, `_llm_validate` for input/output/tool-call protocol methods) implement the same four fail-closed branches.
**Invariant:** ambiguity never passes — every non-PASS path (unclear reply, no LLM, unusable LLM type, exception) returns False through BOTH entry points; regeneration is bounded by `max_guardrail_retries` and each attempt carries the previous failure reason; a clean "PASS" inside a markdown fence is NOT a pass (the test pins exactly this trap).
**Probe:** `tests/unit/test_llm_guardrail_fail_closed.py` (whole file, 91 lines) pins the contract — a stub LLM replying "```
PASS
```" yields `is_valid is False` through `__call__`; a refusal ("I cannot help with that.") yields False; `test_both_entry_points_agree_on_ambiguous_reply` asserts `call_valid is validate_valid is False` for the same ambiguous reply; clean "PASS"/"FAIL: bad" still behave; a get_response-only stub is accepted rather than rejected as "Invalid LLM instance" (issue #3631).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "praisonai", query: "guardrail retry regenerate fail closed LLM judge", name_pattern: "^_apply_guardrail_with_retry$|^LLMGuardrail$|^_llm_validate$", limit: 10 });
```

## Verdict
Adopt both halves as one contract: bounded regeneration whose prompt carries the validator's exact error (feedback-driven repair, not blind resampling), and a judge whose only accepting branch is a clean PASS prefix with every other outcome — including exceptions — mapping to False. Adopt the dual-entry-point parity requirement explicitly (two public surfaces must not drift). Adapt the judge prompt to your host's LLM interface ladder (`chat`/`get_response`/callable) and the BackoffPolicy source to your config system. Omit praisonai's TaskOutput typing and CrewAI-lineage prompt wording. Coverage: no recorded index issue on cited paths; the fail-closed contract is directly and exhaustively tested; the regeneration loop wiring in agent.py is verified by read, not by a dedicated test.
