<!-- capsule-v2 -->
# Custom callback hook surface — which hooks must an observability integration implement, and when does each fire?

**Source:** litellm MIT `litellm_internal_staging@f005afa1`; Codebase Memory `litellm`. **Question:** What is the complete CustomLogger hook contract (sync vs async, logging vs transformation), and what class-level flags change dispatch behavior?

## `CustomLogger`
**Path/Symbol:** `litellm/integrations/custom_logger.py:CustomLogger` (:61-1065); sync hooks (:135-148); async twins + `async_pre_request_hook` (:150-189); `enforces_request_content` flag doc (:64-80).
**Signature:** `class CustomLogger:` with `__init__(self, turn_off_message_logging=False, message_logging=True, **kwargs)`.
**Data Shape:** every log hook receives `(kwargs, response_obj, start_time, end_time)` where `kwargs["litellm_params"]` carries the per-call context; pre-call hooks receive `(model, messages, kwargs)` / `(user_api_key_dict, cache, call_type, ...)` depending on entrypoint.

### Decisive source
```python
    enforces_request_content: bool = False
    """
    Whether this hook's ``async_pre_call_hook`` judges the request payload itself.
    False for the accounting hooks, which count a request rather than read it: rate limits,
    parallel slots, budgets, cache lookups. Those must run once per request and never once per
    record of a batch upload, which would charge a caller once for every line of their file.
    ...
    Only the leaf class is consulted, so a subclass that does not override ``async_pre_call_hook`` inherits nothing.
    """

    def log_pre_api_call(self, model, messages, kwargs): pass
    def log_post_api_call(self, kwargs, response_obj, start_time, end_time): pass
    def log_stream_event(self, kwargs, response_obj, start_time, end_time): pass
    def log_success_event(self, kwargs, response_obj, start_time, end_time): pass
    def log_failure_event(self, kwargs, response_obj, start_time, end_time): pass

    async def async_log_pre_api_call(self, model, messages, kwargs): pass

    async def async_log_success_event(self, kwargs, response_obj, start_time, end_time): pass
    async def async_log_failure_event(self, kwargs, response_obj, start_time, end_time): pass
```
(:64-79 condensed, :135-187) — the transformation hook is distinct from logging:
```python
    async def async_pre_request_hook(self, model: str, messages: list, kwargs: dict) -> dict | None:
        """
        Hook called before making the API request to allow modifying request parameters.
        Unlike async_log_pre_api_call (which is for logging), this hook is meant for transformations.
        Returns: Optional[Dict]: Modified kwargs to use for the request, or None
        ```
(:158-181)

**Flow:** integrations subclass CustomLogger, register as callbacks, and `litellm_logging.Logging` fans events out: pre-api-call (before request), stream event (per chunk), success/failure (terminal, sync AND async variants dispatched by call mode), audit-log event for durable records. Failure events fire from the same exception-mapping boundary that `completion()` uses.
**Invariant:** accounting hooks (rate limits/budgets/cache) run once per request — content-inspecting hooks must opt in via `enforces_request_content = True`; hook lookup consults the leaf class only (no inherited hook dispatch); message redaction is controlled by `turn_off_message_logging` at init.
**Probe:** structural contract verified by reading the base class at the pin; fan-out pinned by direct tests e.g. `_SuccessCapturingLogger.async_log_success_event` in `tests/test_litellm/litellm_core_utils/test_litellm_logging.py` (:4277+).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "litellm", qn_pattern: "integrations\\.custom_logger", name_pattern: "CustomLogger" });
// rank-1 → litellm.litellm.integrations.custom_logger.CustomLogger Class :61-1065 (verified at pin;
// note the identically-named Rust trait in litellm-rust/crates/ai-gateway is a different surface — do not cite it for Python porting)
```

## Verdict
Adopt the hook taxonomy: five sync log points + async twins, one transformation pre-request hook returning modified kwargs, leaf-class-only consultation, and the accounting-vs-content flag. Adapt hook signatures to your event envelope and your redaction flag names. Omit proxy-only registry plumbing (`get_callback_env_vars` reads the proxy AllCallbacks catalog) unless building a proxy; the SDK kernel needs none of it. Next-pass target: the fan-out order itself inside `litellm_logging.Logging.success_event/failure_event`.
