<!-- capsule-v2 -->
# stop-lifecycle-profile-cleanup — graceful close, kill escalation, and the temp-profile removal ladder

**Source:** zendriver MIT `main@2c6d9c7daaab543d34e9fe2b0ef7eaa171c79760`; Codebase Memory `ext-zendriver`. **Question:** What is the full shutdown order, and why can stop() be called repeatedly?

## CDP close → terminate → 3s grace → kill → rmtree retries
**Path/Symbol:** `zendriver/core/browser.py:Browser.stop` (:610-648), `_cleanup_temporary_profile` (:650-669), `stopped` property (:176-177).
**Signature:** `async def stop(self) -> None`; `@property def stopped(self) -> bool  # not (process and poll() is None)`.
**Data Shape:** termination budget = 12 × 0.25s polls; profile removal = 5 attempts × 0.15s sleeps.

### Decisive source
```python
if self._process:
    try:
        self._process.terminate()
        for _ in range(12):
            if self._process.returncode is not None:
                break
            await asyncio.sleep(0.25)
        else:
            logger.debug("browser process did not stop. killing it")
            self._process.kill()
        await asyncio.to_thread(self._process.wait)
    except ProcessLookupError:
        # ignore this well known race condition because it only means that
        # the process was not found while trying to terminate or kill it
        pass
    self._process = None
    self._process_pid = None
```

**Flow:** early-return when nothing to do (idempotency) → try `cdp.browser.close()` over the connection, swallowing failure with "Likely the browser is already gone" → `connection.aclose()` → process ladder above → profile cleanup only when the dir was auto-created (`uses_custom_data_dir` guard). `create()` also registered an `asyncio_atexit` hook calling `stop()` + cleanup, so interpreter exit converges too.
**Invariant:** every step tolerates "already dead": CDP close may throw, terminate/kill may hit ProcessLookupError, rmtree may FileNotFoundError — each is caught and folded into convergence rather than raised. A port that lets any of these propagate breaks context-manager exits on already-stopped browsers.
**Probe:** direct tests pin idempotent shutdown: `tests/core/test_browser.py::test_browser_stop_can_be_called_on_a_closed_connection` (:46), `::test_browser_stop_can_be_called_multiple_times` (:62), `::test_browser_stopped_is_true_after_calling_stop` (:72).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-zendriver", query: "Browser stop terminate kill", limit: 5 });
```

## Verdict
Adopt the converge-don't-raise ladder verbatim; adapt budgets to your platform's exit latency; keep the custom-dir guard or you will delete user profiles.
