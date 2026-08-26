<!-- capsule-v2 -->
# Local browser watchdog — subprocess launch with temp-dir fallback + graceful teardown

**Source:** browser-use MIT `main@3c989dc`; Codebase Memory `browser-use`. **Question:** how does an agent launch a local Chrome/Chromium subprocess over CDP, recover from profile-lock failures, and tear it down cleanly?

## Connected graph-selected seam
**Path/Symbol:** `browser_use/browser/watchdogs/local_browser_watchdog.py` (506 lines): `LocalBrowserWatchdog` (:29) — `on_BrowserLaunchEvent` (:49-63), `on_BrowserKillEvent` (:65-83), `on_BrowserStopEvent` (:85-90), `_launch_browser` (:93-217), `_find_installed_browser_path` (:220-358), `_install_browser_with_playwright` (:360-394), `_find_free_port` (:396-405), `_wait_for_cdp_url` (:408-428), `_cleanup_process` (:431-461), `_cleanup_temp_dir` (:463-478).
**Signature:** `_launch_browser(max_retries=3) -> (psutil.Process, cdp_url)`.

### Decisive source
```python
# Retry ladder on user_data_dir lock errors (singletonlock / user data directory / cannot create / already in use):
#   for attempt in range(max_retries):
#       try: launch with profile.get_args() + --remote-debugging-port=<free port>
#       except lock error and attempt < max-1:
#           tmp_dir = mkdtemp('browseruse-tmp-'); profile.user_data_dir = str(tmp_dir); retry
#       else: restore original user_data_dir, cleanup temp dirs, raise
# Binary discovery: custom executable_path > channel-specific paths > Playwright bundled Chromium >
#   system Chrome > Chromium/Canary/Brave/Edge > playwright install (uvx, --with-deps Linux only)
#   glob matches sorted, take LAST (alphanumerically highest version)
# Teardown: terminate() -> poll 50x0.1s -> kill() if still running; only rmtree dirs named 'browseruse-tmp-'
```

**Flow:** on launch → save original user_data_dir → find free port → discover/install binary → `create_subprocess_exec` → wait for CDP `/json/version` (200) → on lock error, retry with a fresh temp user_data_dir → on success, clean unused temp dirs → on kill, terminate-then-kill the process, restore user_data_dir, rmtree temp dirs.
**Invariant:** a lock failure never leaves the profile's user_data_dir pointing at a temp dir (restored on failure AND on kill); temp dirs are only removed if named `browseruse-tmp-`; the launch asserts `--user-data-dir` is present (Chrome won't attach via CDP otherwise); `--with-deps` is Linux-only (fails on Windows/macOS).
**Probe:** `tests/ci/browser/test_session_start.py`, `tests/ci/browser/test_profile_copy.py`, `tests/ci/test_browser_use_cli.py`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "browser-use", query: "LocalBrowserWatchdog _launch_browser singletonlock _find_installed_browser_path _cleanup_process", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the temp-dir retry ladder for profile locks, the channel-prioritized binary discovery, and the terminate-then-kill teardown. Adapt the browser-path table to host OS.
