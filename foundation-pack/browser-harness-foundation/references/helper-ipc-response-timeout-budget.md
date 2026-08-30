<!-- capsule-v2 -->
# Per-call IPC response budgets — how do you keep a one-shot request/response socket from hanging forever on a slow CDP call without breaking long-running operations like cloud screenshots?

**Source:** browser-harness MIT `main@6bb1c847fd62638554618e8d1e03247b935ff9cf`; Codebase Memory `browser-harness`. **Question:** The IPC connect already has a timeout — why does the *response* need its own budget, how is it threaded to specific calls, and what does a typed timeout buy the caller?

## Connect-vs-response split + typed timeout + private-kwarg threading
**Path/Symbol:** `src/browser_harness/helpers.py`: constants (:41-45), `_IPCResponseTimeout` (:48-49), `_send` (:52-63), `cdp` (:66-71), `capture_screenshot` (:258-280).

**Signature:** `def _send(req, response_timeout=DEFAULT_IPC_RESPONSE_TIMEOUT_SECONDS)`; `def cdp(method, session_id=None, _response_timeout=DEFAULT_IPC_RESPONSE_TIMEOUT_SECONDS, **params)`; `class _IPCResponseTimeout(TimeoutError)`.

**Data Shape:** `IPC_CONNECT_TIMEOUT_SECONDS = 5.0`, `DEFAULT_IPC_RESPONSE_TIMEOUT_SECONDS = 5.0`, `SCREENSHOT_IPC_RESPONSE_TIMEOUT_SECONDS = 60.0` (kept "within the caller's existing 90-second process budget").

### Decisive source
```python
def _send(req, response_timeout=DEFAULT_IPC_RESPONSE_TIMEOUT_SECONDS):
    c, token = ipc.connect(NAME, timeout=IPC_CONNECT_TIMEOUT_SECONDS)
    try:
        c.settimeout(response_timeout)
        try:
            r = ipc.request(c, token, req)
        except TimeoutError as e:
            raise _IPCResponseTimeout from e
    finally:
        c.close()
    if "error" in r: raise RuntimeError(r["error"])
    return r
```

**Flow:** every request connects with the fixed 5s connect budget, then `settimeout(response_timeout)` arms a *per-call* read budget before `ipc.request`; a socket `TimeoutError` is rethrown as the typed `_IPCResponseTimeout` subclass **with the original as `__cause__`**; the socket always closes in `finally`. `cdp()` threads the budget through a single-leading-underscore keyword (`_response_timeout`) so it can never be mistaken for (or collide with) a CDP param — everything else in `**params` goes onto the wire. `capture_screenshot` opts into 60s for `Page.captureScreenshot` and converts a typed timeout into `RuntimeError(f"Page.captureScreenshot timed out after {SCREENSHOT_IPC_RESPONSE_TIMEOUT_SECONDS:g}s") from e`, so agents see an instruction-shaped error while the cause chain preserves the timeout evidence.

**Invariant:** The connect timeout must stay short and independent (a dead daemon fails fast on *every* call); the response budget must be settable per call because one CDP method's latency ceiling is not the daemon's. The private-kwarg boundary is load-bearing: forwarding `_response_timeout` into CDP params would corrupt the wire request (test-pinned). Typed exceptions let callers distinguish "daemon slow" from "daemon gone" without string matching.

**Probe:** `tests/unit/test_helpers.py` — `test_send_keeps_connect_timeout_short_and_sets_response_budget` (:32-49: connect called with `IPC_CONNECT_TIMEOUT_SECONDS`, `socket.timeouts == [60.0]`); `test_screenshot_uses_long_response_timeout_without_forwarding_it_to_cdp` (:52-67: request dict contains only `{method, params, session_id}`; kwargs exactly `{"response_timeout": 60.0}`); `test_screenshot_timeout_has_context` (:70-73: `RuntimeError` matches `"Page.captureScreenshot timed out after 60s"`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.get_code_snippet({ project: "browser-harness", qualified_name: "browser-harness.src.browser_harness.helpers._send" });
```
Returns :52-63 byte-identical to the excerpt above; `trace_path inbound _send depth=1` shows the seven helper entry points that inherit the default budget (verified live this pass).

## Verdict
Adopt the connect/response timeout split, typed timeout rethrow with cause chaining, and underscore-private kwarg threading where a public API also owns arbitrary passthrough params; adapt the numeric budgets (60s here exists because cloud screenshot round trips dwarf ordinary CDP calls) and the `:g` seconds formatting; omit the Browser Use rationale. Coverage caveat: none — three direct unit tests pin this seam at this pin, all GREEN ambient.
