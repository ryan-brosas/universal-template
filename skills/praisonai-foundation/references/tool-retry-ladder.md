<!-- capsule-v2 -->
# Tool retry ladder — when does a failed tool call get retried, and what must always short-circuit the retry?

**Source:** praisonai MIT `main@d82364ec23a83fd9a6e2e849a5285442b4734ca3`; Codebase Memory `praisonai`. **Question:** Given a failed tool call (error dict or exception), what decides retry-vs-stop, which outcomes must *never* be retried, and how is the governing RetryPolicy chosen?

## ToolExecutionMixin._execute_tool_with_circuit_breaker retry loop
**Path/Symbol:** `src/praisonai-agents/praisonaiagents/agent/tool_execution.py:ToolExecutionMixin._execute_tool_with_circuit_breaker` (lines 2081–2191). Policy dataclass: `praisonaiagents/tools/retry.py:RetryPolicy` (lines 11–62). Policy resolution: `_get_tool_retry_policy` → `_effective_tool_retry_policy` (lines 3075–3115+). Non-idempotency veto: `_tool_declares_not_idempotent` (lines 2999–3027).
**Signature:** `_execute_tool_with_circuit_breaker(self, function_name, arguments)` → success result, error dict, or raised `ToolExecutionError`. `RetryPolicy(max_attempts=3, backoff_factor=2.0, initial_delay_ms=1000, max_delay_ms=30000, retry_on={"timeout","rate_limit","connection_error"}, jitter=False, jitter_factor=0.25)` with `should_retry(error_type, attempt)` and `get_delay_ms(attempt)`.

### Decisive source
```python
retry_policy = self._get_tool_retry_policy(function_name)
for attempt in range(retry_policy.max_attempts):
    try:
        result = self._execute_tool_with_circuit_breaker_impl(function_name, arguments)
        if isinstance(result, dict) and result.get("error"):
            # Skip retry for non-retryable errors (approval, permission, etc.)
            if (result.get("approval_denied") or result.get("permission_denied") or
                result.get("approval_error") or result.get("policy_denied") or
                result.get("guardrail_denied") or result.get("circuit_open")):
                return result
            # The body already ran and may have completed its side effect
            # before failing. Honour an explicit non-idempotent declaration
            # rather than re-driving it (send a second email, charge twice).
            if self._tool_declares_not_idempotent(function_name):
                return result
            error_type = self._classify_error_type(result, last_exception)
            if not retry_policy.should_retry(error_type, attempt):
                return result
            if attempt == retry_policy.max_attempts - 1:
                return result
            delay_ms = retry_policy.get_delay_ms(attempt)
            self._emit_retry_hook(function_name, attempt + 1, delay_ms, ...)
            time.sleep(delay_ms / 1000.0)
            continue
        else:
            return result
    except ToolExecutionError as e:
        last_exception = e
        if not e.is_retryable or attempt == retry_policy.max_attempts - 1:
            raise
        ...
    except Exception as e:
        is_retryable = not isinstance(e, (ValueError, TypeError, AttributeError))
        wrapped_error = ToolExecutionError(f"Tool '{function_name}' failed: {e}",
                                           tool_name=function_name, agent_id=self.name,
                                           is_retryable=is_retryable)
        if not is_retryable or attempt == retry_policy.max_attempts - 1:
            raise wrapped_error from e
        ...
```

**Flow:** resolve ONE policy for the tool (precedence: per-tool `.retry_policy` > agent-level `ToolConfig(retry_policy=...)` > policy translated from ExecutionConfig's second vocabulary — `max_retry_limit` counts *retries* so total runs = limit+1, delays in seconds, jitter as fraction; non-iterable MCP tool objects never crash the lookup) → loop `max_attempts` times: success → return; error dict → six denial keys short-circuit immediately, then an *explicit* non-idempotent declaration vetoes retry (distinct from the fail-safe `_is_tool_idempotent`, which answers False for unknown tools — gating on that would stop retrying every unregistered user tool), then classify error type + `should_retry(error_type, attempt)` + last-attempt check → emit retry hook, sleep capped exponential backoff (optional ±25% jitter), continue; `ToolExecutionError` honors its own `.is_retryable`; bare exceptions are wrapped with `is_retryable = not isinstance(e, (ValueError, TypeError, AttributeError))` — programming errors are never retried.
**Invariant:** denial-keyed results (`approval_denied`, `permission_denied`, `approval_error`, `policy_denied`, `guardrail_denied`, `circuit_open`) are returned on the FIRST occurrence — they are policy outcomes, not transient faults; a tool that explicitly declares itself non-idempotent is never re-driven after failure (the body may have landed its side effect); the last attempt always returns/raises without sleeping; `RetryPolicy.__post_init__` rejects `max_attempts < 1`, `backoff_factor < 1.0`, negative initial delay, `max_delay < initial_delay`, and out-of-range jitter factor.
**Probe:** `tests/unit/test_tool_retry_integration.py:52–110` — a flaky tool raising "Connection timeout" succeeds on attempt 3 with patched sleep (`call_count == 3`), while a `permission_denied` error-dict tool runs exactly once (`call_count == 1`); `:241–315` pins the precedence ladder (tool-level `max_attempts=1` beats agent-level 5; agent-level beats default 3; MCP non-iterable tools fall back to default without crashing). `tests/unit/tools/test_retry.py:12–134` pins defaults, exponential growth, the 30000ms cap, the jitter band, and all five validation errors.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "praisonai", query: "tool retry policy denial non-idempotent backoff", name_pattern: "^RetryPolicy$|^_effective_tool_retry_policy$|^_tool_declares_not_idempotent$", limit: 10 });
```

## Verdict
Adopt the layered decision order (denial keys → explicit non-idempotency → classified should_retry → last-attempt) and the "explicit declaration only" veto semantics — it is the difference between safe selective vetoes and accidentally disabling retries for every unregistered tool. Adopt the single-vocabulary translation point where two config spellings of the same knobs meet. Adapt the denial-key vocabulary to your host's permission/approval system and the `(ValueError, TypeError, AttributeError)` programming-error set to your language's idioms. Omit praisonai's hook-emission side channel unless your host has one. Coverage: no recorded index issue on cited paths; both the policy dataclass and the integration ladder are directly tested.
