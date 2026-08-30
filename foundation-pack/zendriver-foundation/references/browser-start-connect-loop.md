<!-- capsule-v2 -->
# browser-start-connect-loop — launch, poll the DevTools HTTP endpoint, then build the browser-level connection

**Source:** zendriver MIT `main@2c6d9c7daaab543d34e9fe2b0ef7eaa171c79760`; Codebase Memory `ext-zendriver`. **Question:** What is the exact startup sequence from `Browser.create` to usable targets?

## create → start → test_connection retries → Connection + target discovery
**Path/Symbol:** `zendriver/core/browser.py:Browser.create` (:67-111), `start` (:314-436), `test_connection` (:438-447), `stop` (:610-648).
**Signature:** `@classmethod async def create(cls, config=None, **kw) -> Browser`; `async def start(self) -> Browser`.
**Data Shape:** connection knobs on Config: `browser_connection_timeout=0.25`, `browser_connection_max_tries=10`. `asyncio_atexit.register(browser_atexit)` in `create()` guarantees stop+temp-profile cleanup even on unhandled exit.

### Decisive source
```python
self._http = HTTPApi((self.config.host, self.config.port))
util.get_registered_instances().add(self)
await asyncio.sleep(self.config.browser_connection_timeout)
for _ in range(self.config.browser_connection_max_tries):
    if await self.test_connection():
        break
    await asyncio.sleep(self.config.browser_connection_timeout)
if not self.info:
    ...
    stderr = await util._read_process_stderr(self._process)
    logger.info("Browser stderr: %s", ...)
    await self.stop()
    raise Exception("Failed to connect to browser ...")
```

**Flow:** `create()` enforces async construction (bare `__init__` raises RuntimeError :120-127) → `start()`: connect-existing shortcut when host AND port are set, else assign `127.0.0.1:free_port()`; append extension/lang args; spawn process via `util._start_process` with `about:blank`; poll `/json/version` until it returns (populating `self.info = ContraDict(...)`); build `Connection(info.webSocketDebuggerUrl)`; if `autodiscover_targets` (Config default True) attach `_handle_target_update` handlers for TargetInfoChanged/Created/Destroyed/Crashed and send `target.set_discover_targets(discover=True)`; finally `update_targets()`.
**Invariant:** the retry loop's total budget is `timeout × max_tries` plus per-attempt HTTP latency — on slow-starting browsers this *is* the failure mode ("Failed to connect"), and stderr is logged before raising precisely because the cause is usually visible there. Also `stop()` sends CDP `browser.close()` first and only falls back to terminate→kill after 12×0.25s.
**Probe:** direct test pins the failure path end-to-end with a mocked `test_connection`: `tests/core/test_browser.py::test_connection_error_raises_exception_and_logs_stderr` asserts `"Browser stderr" in caplog.text`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-zendriver", query: "Browser start test_connection", limit: 5 });
```

## Verdict
Adopt the HTTP-poll-before-WS ordering and the atexit safety net; tune timeout/max_tries for your host (defaults are tight); omit the autodiscover event wiring only if you manage targets by explicit refresh.
