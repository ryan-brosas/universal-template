<!-- capsule-v2 -->
# Router timeout resolution chain — which rung wins when several timeouts are set?

**Source:** litellm MIT `litellm_internal_staging@f005afa1460385a218be8ef1fdfa49998bf93523`; Codebase Memory `litellm`. **Question:** When a per-request timeout, a per-deployment timeout, a router-level `timeout`, and a global `litellm.request_timeout` all exist, which value reaches the HTTP client, and when does it stay an `httpx.Timeout` versus collapse to a float?

## Three-stage resolution (Router init → per-deployment kwargs → completion coercion)
**Path/Symbol:** `litellm/router.py:Router.__init__` (:691-697), `Router._update_kwargs_with_deployment` (:3320-3322), `Router._get_stream_timeout` (:3353-3361) / `_get_non_stream_timeout` (:3363-3374) / `_get_timeout` (:3376-3385); then `litellm/litellm_core_utils/completion_timeout.py:CompletionTimeout.resolve` (:33-70) called from `litellm/main.py:5276-5282`; gate `litellm/utils.py:supports_httpx_timeout` (:2229-2238).
**Signature:** `_get_timeout(self, kwargs: dict, data: dict) -> float | int | None`; `CompletionTimeout.resolve(model_timeout: float | str | httpx.Timeout | None, kwargs: dict, custom_llm_provider: str, *, global_timeout: float | str | None, supports_httpx_timeout: Callable[[str], bool]) -> float | httpx.Timeout`.
**Data Shape:** `data` is the deployment's `litellm_params` dict; resolved value is written to `kwargs["timeout"]` before provider dispatch; terminal type is `float` or `httpx.Timeout`.

### Decisive source
```python
# router.py:3363-3385 — non-stream ladder; stream ladder mirrors it
timeout: Final = (
    kwargs.get("timeout", None)          # params dynamically set by user
    or kwargs.get("request_timeout", None)
    or data.get("timeout", None)         # timeout on litellm_params for this deployment
    or data.get("request_timeout", None)
    or self.request_timeout              # explicitly-configured litellm.request_timeout (per-attempt)
    or self.timeout                      # router_settings.timeout (or package default 600)
    or self.default_litellm_params.get("timeout", None)
)
```
```python
# completion_timeout.py:62-68 — coercion at the end of resolve()
if isinstance(resolved, httpx.Timeout) and not supports_httpx_timeout(custom_llm_provider):
    read_timeout: Final = resolved.read
    resolved = (
        float(read_timeout) if read_timeout is not None else COMPLETION_HTTP_FALLBACK_SECONDS
    )  # default 10 min timeout
elif not isinstance(resolved, httpx.Timeout):
    resolved = float(resolved)
```

**Flow:** (1) Router init: `self.timeout = timeout or litellm.request_timeout`, but the separate per-attempt rung `self.request_timeout` is stored **only when a router-level `timeout=` was also passed**: `self.request_timeout = get_configured_request_timeout() if timeout is not None else None`. (2) Per call, after deployment selection, `kwargs["timeout"] = self._get_timeout(kwargs, deployment["litellm_params"])`: stream requests try `_get_stream_timeout` first (`stream_timeout` kwargs > deployment > router > `self.request_timeout` > default_litellm_params); any None falls through to `_get_non_stream_timeout`. (3) `main.completion` then re-resolves through `CompletionTimeout.resolve(timeout, kwargs, custom_llm_provider, global_timeout=get_configured_request_timeout(), ...)` with order model_timeout > `kwargs["timeout"]` > `kwargs["request_timeout"]` > explicit global, falling back to `COMPLETION_HTTP_FALLBACK_SECONDS` = 600 when nothing was configured. (4) Coercion: an `httpx.Timeout` survives only for providers in `{openai, azure, bedrock}`; otherwise it degrades to its `read` component as a plain float.
**Invariant:** First-non-None-wins with truthiness (`or`) — a literal `0` timeout never wins a rung. An explicit global 6000 must be honored, never silently truncated to the 600 sentinel; only *unset* globals fall back to 600. The explicit-global signal is `request_timeout_explicitly_set` (true iff `REQUEST_TIMEOUT` env was set) OR runtime value ≠ `DEFAULT_REQUEST_TIMEOUT_SECONDS` (`litellm/litellm_core_utils/request_timeout_resolver.py:20-29`).
**Probe:** `tests/test_litellm/test_completion_timeout_resolution.py` (10 tests: explicit-wins, alias rungs, 600 fallback, 6000 preservation ×3, httpx.Timeout coerced→50.0 for azure_ai, preserved-by-identity for openai) and `tests/test_litellm/test_router.py::TestRouterRequestTimeoutPropagation` (:6644-6710, 8 tests: router.timeout vs request_timeout stored independently; request_timeout beats router.timeout in stream and non-stream; explicit stream_timeout=45 still wins; per-deployment 120 beats explicit global 300; per-request 60 beats per-deployment 120). Both executed live at the pin: 10 passed + 8 passed.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "litellm", query: "_get_non_stream_timeout", limit: 3 });
// → rank-1 exact: litellm.litellm.router.Router._get_non_stream_timeout (litellm/router.py 3363-3374)
await mcp.codebase_memory.search_graph({ project: "litellm", query: "CompletionTimeout resolve coerce httpx.Timeout", limit: 3 });
// → rank-1: CompletionTimeout.resolve (completion_timeout.py 33-70)
```
Adversarial check executed: prose query "how does litellm decide which HTTP timeout applies to a streamed router request" returns only test names/noise — production symbols need the name needles above.

## Verdict
Adopt the three-stage ladder, the event of writing the resolved value into `kwargs["timeout"]` once per deployment pick, the {openai, azure, bedrock}-only `httpx.Timeout` allowlist with read-component coercion, and the explicit-vs-default distinction for the global timeout. Adapt the sentinel constant (600s) and provider allowlist to your host's provider set. Omit the legacy decorator `litellm/timeout.py` (thread/asyncio wait_for wrapper, zero callers) — it is dead weight next to this path. Coverage caveat: none; all cited paths no_recorded_issue, full mode.
