<!-- capsule-v2 -->
# Model policy — exact-settings precedence and bounded retry backoff

**Source:** Aider Apache-2.0 `main@5dc9490bb35f9729ef2c95d00a19ccd30c26339c`; Codebase Memory project `aider` (full index). **Question:** How does a harness pick per-model settings with precedence and limit provider retries instead of looping forever?

## Exact-settings precedence and capped backoff
**Path/Symbol:** `aider/models.py`: `Model.configure_model_settings(model)` (:385), `send_completion(...)` (:958), `simple_send_with_retries(messages)` (:1039); `RETRY_TIMEOUT = 60` (:26), `request_timeout = 600` (:28).
**Signature:** `configure_model_settings(model) -> None`; `simple_send_with_retries(messages) -> str | None`.
**Data Shape:** `MODEL_SETTINGS` entries carry capability flags and `extra_params`; `aider/extra_params` deep-merges its nested dicts last; on success reasoning content is stripped from the returned text.

### Decisive source
```python
def configure_model_settings(self, model):
    for ms in MODEL_SETTINGS:
        if model == ms.logname:
            self._copy_fields(ms); exact_match = True; break
    if not exact_match:
        self.apply_generic_model_settings(model)
    # user's aider/extra_params deep-merges last
    if self.extra_model_settings and self.extra_model_settings.name == "aider/extra_params":
        for key, value in self.extra_model_settings.extra_params.items():
            if isinstance(value, dict) and isinstance(self.extra_params.get(key), dict):
                self.extra_params[key] = {**self.extra_params[key], **value}
            else:
                self.extra_params[key] = value
# bounded retry: backoff doubles 0.125s up to the 60s cap, then returns None
while True:
    ...
    retry_delay *= 2
    if retry_delay > RETRY_TIMEOUT:
        should_retry = False
    if not should_retry:
        return None
    time.sleep(retry_delay)
```

**Flow:** apply exact match, else generic; then deep-merge `aider/extra_params` last; `send_completion` builds kwargs honoring capability flags and provider overrides; `simple_send_with_retries` sends, doubling delay up to `RETRY_TIMEOUT` on retryable exceptions, stripping reasoning on success.
**Invariant:** an exact declaration beats generic rules and `aider/extra_params` overrides both; non-retryable errors or backoff past the 60s cap terminate the loop (return `None`); reasoning content is stripped from the returned text.
**Probe:** `tests/basic/test_models.py::test_configure_model_settings` (:382), `test_aider_extra_model_settings` (:374), `tests/basic/test_sendchat.py::test_simple_send_with_retries_rate_limit_error` (:24).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "aider", query: "configure_model_settings simple_send_with_retries RETRY_TIMEOUT", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt exact-match-then-generic precedence and the capped doubling backoff as the provider policy. Keep the transport and exception table host-specific; port the precedence and bounded-retry contract.
