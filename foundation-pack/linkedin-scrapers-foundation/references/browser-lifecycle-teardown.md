<!-- capsule-v2 -->
# Browser lifecycle & teardown choreography — how do you start a browser, discover its targets, and tear it down so no orphan process survives?

**Source:** zendriver AGPL-3.0 — PATTERNS ONLY, never copy verbatim. `main@2c6d9c7d`; Codebase Memory `ext-zendriver`. **Question:** what is the correct start→connect→target-discover→stop sequence for a CDP-driven browser, and how do you guarantee the child process is fully dead?

## Async factory + HTTP-version poll + autodiscover + graceful-then-kill stop
**Path/Symbol:** `zendriver/core/browser.py:Browser` (:31-673), `Browser.create` (:67-111), `start` (:314-436), `stop` (:610-648), `_cleanup_temporary_profile` (:650-670); `util._start_process`/`_read_process_stderr` (`core/util.py:324-361`).
**Signature:** `await Browser.create(config) -> Browser` (async factory — the class is NOT instantiated directly); `Browser.start()`; `Browser.stop()`; `Browser.get(url, new_tab, new_window)`.
**Data Shape:** `_process: subprocess.Popen` + `_process_pid`; `_http: HTTPApi` (JSON-over-HTTP to `/json/version`); `targets: List[Connection]`; `connection: Connection` (browser-level WS). `config.browser_connection_timeout=0.25`, `browser_connection_max_tries=10`.

### Decisive source
```python
# start: spawn with close_fds on posix, then poll HTTP /json/version
self._process = util._start_process(exe, params, is_posix)   # stdin/out/err=PIPE, close_fds=is_posix
self._http = HTTPApi((self.config.host, self.config.port))
await asyncio.sleep(self.config.browser_connection_timeout)
for _ in range(self.config.browser_connection_max_tries):
    if await self.test_connection(): break          # GET /json/version -> self.info
    await asyncio.sleep(self.config.browser_connection_timeout)
if not self.info:                                   # failed: read stderr, stop, raise
    stderr = await util._read_process_stderr(self._process)
    await self.stop(); raise Exception("Failed to connect to browser ...")
# stop: send browser.close, then terminate, wait 3s, else kill
try: await self.connection.send(cdp.browser.close())
except Exception: logger.warning("...browser already gone...")
self._process.terminate()
for _ in range(12):                                  # 12 x 0.25s = 3s grace
    if self._process.returncode is not None: break
    await asyncio.sleep(0.25)
else: self._process.kill()                           # grace exceeded -> SIGKILL
await asyncio.to_thread(self._process.wait)
```

**Flow:** `create` → `start`: spawns the browser with piped stdio (`close_fds=is_posix` so no fd leaks), polls `GET /json/version` over HTTP up to `max_tries` (10×0.25s), then opens the browser-level WS to `webSocketDebuggerUrl`. If `autodiscover_targets`, registers target-event handlers (TargetInfoChanged/Created/Destroyed/Crashed) and sends `Target.setDiscoverTargets(discover=True)` so new tabs auto-appear in `self.targets`; then `update_targets()` reconciles the initial list. `stop`: sends `Browser.close`, closes the WS, `terminate()`s the process, waits up to 3s for exit, else `kill()`s it, then `wait()`s and cleans the temp profile (5 retries for Windows file locks). `Browser.create` registers an asyncio-atexit hook so an abandoned instance is torn down on loop exit.
**Invariant:** teardown is GRACEFUL-THEN-KILL with a bounded grace window (3s), and `ProcessLookupError` (already-gone race) is swallowed; the temp profile is only removed when NOT a custom `user_data_dir` (so user-supplied profiles survive). The HTTP `/json/version` poll is the readiness gate — no fixed sleep. Cross-reference: linkedin-scrapers' zombie-browser-teardown (linkedin-profile-scraper-api's `close()`-on-every-catch + `treeKill` SIGKILL) and browser-lifecycle — zendriver is the process-level counterpart: same "kill orphan children" goal, CDP-native.
**Probe:** REAL tests — `tests/core/test_browser.py`: `test_connection_error_raises_exception_and_logs_stderr` (:15), `test_browser_stop_can_be_called_on_a_closed_connection` (:46), `test_browser_stop_can_be_called_multiple_times` (:62), `test_browser_stopped_is_true_after_calling_stop` (:72), `test_browser_stopped_is_true_when_stopped_externally` (:78); `tests/core/test_multiple_browsers.py::test_multiple_browsers_diff_userdata` (per-instance profile isolation). Deterministic pins (anchored at the `zendriver/` package dir): `grep -n 'close_fds=is_posix' core/util.py` → :341; `grep -n 'browser_connection_max_tries' core/browser.py` → :378.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-zendriver", query: "Browser.create start stop setDiscoverTargets _cleanup_temporary_profile", limit: 5 });
```

## Verdict
Adopt: async-factory + HTTP-readiness poll + autodiscover + graceful-then-kill teardown with bounded grace and profile-preservation. Adapt the grace window and poll counts to your environment. Omit the asyncio-atexit hook if your runtime manages lifecycle. Coverage: directly test-pinned (5 live browser tests + multi-browser isolation).
