<!-- capsule-v2 -->
# Activity-config layering — re-normalize non-retryable errors after every override merge

## Source / Question
`pydantic_ai_slim/pydantic_ai/durable_exec/temporal/_agent.py` (`_merge_activity_config` :78–88, config normalization :184–203) + `prefect/_durability.py` (:113–121) @ `main@b3cdbc96` (MIT); Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** Durable units need framework errors marked non-retryable (a UserError will never succeed on retry), but users supply per-model/per-toolset config overrides whose retry policy REPLACES the base wholesale — how do you layer configs without silently losing the non-retryable set? A porter will dict-merge and let an oversized payload retry forever (#7110).

## Path / Symbol
`_agent.py` — `_merge_activity_config(base, override)`; base-policy normalization at construction: `retry_policy = copy.copy(activity_config.get('retry_policy') or RetryPolicy())`; `retry_policy.non_retryable_error_types = [*(retry_policy.non_retryable_error_types or []), UserError.__name__, PydanticUserError.__name__, PAYLOAD_SIZE_ERROR_TYPE]`. Prefect twin composes the same condition via `with_non_retryable_errors(default_task_config | (model_task_config or {}))`.

## Signature
```python
def _merge_activity_config(base: ActivityConfig, override: ActivityConfig) -> ActivityConfig:
    merged = base | override
    if 'retry_policy' in override:                       # wholesale replacement happened
        merged['retry_policy'] = with_non_retryable_errors(merged.get('retry_policy'))
    return merged
```

## Data Shape
Non-retryable set = `{UserError, PydanticUserError, PAYLOAD_SIZE_ERROR_TYPE}` (+ engine-specific payload-limit type). Three layers: base activity config (default `start_to_close_timeout=60s` when absent) ← model/toolset layer keyed by id ← per-tool layer keyed by toolset+tool; `False` as a per-tool value means "don't make an activity at all" (IO-free tools).

### Decisive source — the docstring IS the invariant (:79–84)
```python
# The base config's `retry_policy` is normalized with the non-retryable error types (`UserError`,
# over-limit payloads), but a `retry_policy` in the override replaces it wholesale — so the merged
# policy must be re-normalized or an oversized payload would be retried forever.
```
Construction-time hygiene: `copy.copy` both the incoming ActivityConfig and its RetryPolicy before mutating, because "mutating the caller's ActivityConfig or a RetryPolicy shared with other activities would leak the non-retryable entries into them" (:185–186).

**Flow:** constructor normalizes base policy with the non-retryable set → each layer merge that sees a user retry_policy re-runs normalization on the merged result → every activity runs with timeouts AND the misconfiguration-fails-fast property.

**Invariant:** Framework-level permanent errors must stay non-retryable through ANY user override; never mutate caller-owned config objects (copy first); a missing timeout gets a safe default rather than inheriting None.

**Probe:** `tests/test_temporal.py` construction tests assert the normalized policy contents on built agents (grep `non_retryable_error_types` in test_temporal.py); Prefect parity via `with_non_retryable_errors` composition in test_prefect.py model/handler task paths.

## Get live surrounding code
**Retrieve:**
```
search_graph --project mnt-hdd-utopia-inspo-pydantic-ai --query '_merge_activity_config with_non_retryable_errors retry_policy'
```

## Verdict
**Adopt** merge-then-renormalize and copy-before-mutate for any layered durable-unit config. **Adapt** the error-type set to your framework's permanent-error taxonomy. **Omit** nothing.
