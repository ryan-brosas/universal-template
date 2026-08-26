<!-- capsule-v2 -->
# Per-CDP-request timeout wrapper — how do you convert a silently-dead WebSocket into a fast observable error?

**Source:** browser-use MIT `main@3c989dc`; Codebase Memory `browser-use`. **Question:** how do you keep an agent alive when the browser's WebSocket stays "alive" at TCP level but the browser container behind it is dead?

## Connected graph-selected seam
**Path/Symbol:** `browser_use/browser/_cdp_timeout.py` whole file — `TimeoutWrappedCDPClient` (:91), `send_raw` override (:108), `_parse_env_cdp_timeout` (:38), `DEFAULT_CDP_REQUEST_TIMEOUT_S` (:68).
**Signature:** `class TimeoutWrappedCDPClient(CDPClient)` with `cdp_request_timeout_s: float | None = None`; `async def send_raw(self, method: str, params=None, session_id=None) -> dict`.

### Decisive source
```python
# cdp_use's send_raw() awaits a future that only resolves when the browser sends
# a matching response. Observed failure mode against remote cloud browsers: WS
# stays alive at TCP/keepalive layer while the container is dead or the proxy lost
# upstream -> future never resolves -> whole agent hangs.
async def send_raw(self, method, params=None, session_id=None):
    try:
        return await asyncio.wait_for(
            super().send_raw(method=method, params=params, session_id=session_id),
            timeout=self._cdp_request_timeout_s,
        )
    except TimeoutError as e:
        # Raise a PLAIN TimeoutError so existing `except TimeoutError` handlers in
        # browser-use treat this uniformly.
        raise TimeoutError(
            f'CDP method {method!r} did not respond within {self._cdp_request_timeout_s:.0f}s. '
            f'The browser may be unresponsive (silent WebSocket — container crashed or proxy lost upstream).'
        ) from e
# Default 60s: generous for Page.captureScreenshot / printToPDF on heavy pages,
# but well below the 180s agent step timeout. Same finite-positive env guard as
# BROWSER_USE_ACTION_TIMEOUT_S (BROWSER_USE_CDP_TIMEOUT_S).
```

**Flow:** subclass wraps exactly ONE method (`send_raw`) so every typed CDP call inherits the cap → env var parsed with the same nan/inf/≤0 degrade-to-default guard as the action timeout → timeout re-raised as plain `TimeoutError` with diagnostic text (never a custom exception class).
**Invariant:** the wrapper must re-raise builtin `TimeoutError`, not introduce a new type, or existing handler ladders miss it; the CDP cap (60s) must stay BELOW the action cap (180s) so the inner failure surfaces first with the precise method name; both layers share the identical defensive parse because a bad env value would otherwise make every call instant-timeout (nan) or never-timeout (inf).
**Probe:** `tests/ci/test_cdp_timeout.py` — `test_send_raw_times_out_on_silent_server` (:40), `test_send_raw_passes_through_when_fast` (:73), `test_constructor_rejects_invalid_timeout` (:86), `test_default_cdp_timeout_is_reasonable` (:99), `test_parse_env_rejects_malformed_values` (:107).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase-memory.search_graph({ project: "browser-use", query: "TimeoutWrappedCDPClient send_raw cdp_request_timeout_s wait_for", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the single-method wait_for subclass + plain-TimeoutError contract + two-layer timeout ordering (inner < outer); adapt the 60s default to your transport's slowest legitimate call.
