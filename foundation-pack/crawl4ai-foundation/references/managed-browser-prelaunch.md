<!-- capsule-v2 -->

# Managed browser lifecycle: pre-launch cleanup and escalation shutdown — What must be cleaned BEFORE launching Chromium over CDP, and how do you shut it down without orphaning renderer children?

**Source:** crawl4ai Apache-2.0 `main@7e801521428ee12509994d39151006f64055ebe3`; Codebase Memory `ext-crawl4ai`. **Question:** What must be cleaned BEFORE launching Chromium over CDP, and how do you shut it down without orphaning renderer children?

## Pre-launch port/lock hygiene + escalating kill

**Path/Symbol:** `crawl4ai/browser_manager.py:ManagedBrowser.start (174-277), cleanup (409-458), build_browser_flags (70-125); BrowserManager._verify_cdp_ready (1013-1055)`.

**Signature:** `async def start(self) -> str  # returns CDP endpoint; async def cleanup(self); static build_browser_flags(config) -> List[str]`.

**Data Shape:** Launches via subprocess.Popen with os.setpgrp (Unix) / DETACHED_PROCESS|CREATE_NEW_PROCESS_GROUP (Win). Flags deduped via dict.fromkeys. CDP readiness probed at /json/version.

### Decisive source
```python
# remove Chromium singleton locks, or new launch exits with
                # "Opening in existing browser session."
                for f in ("SingletonLock", "SingletonSocket", "SingletonCookie"):
                    fp = os.path.join(self.user_data_dir, f)
                    if os.path.exists(fp):
                        os.remove(fp)
            ...
                self.browser_process.terminate()
                for _ in range(10):  # 10 attempts, 100ms each
                    if self.browser_process.poll() is not None:
                        break
                    await asyncio.sleep(0.1)
                if self.browser_process.poll() is None:
                    ...os.killpg(os.getpgid(self.browser_process.pid), signal.SIGKILL)...
```

**Flow:** start: cdp_url passthrough -> mkdtemp profile if needed -> kill any process holding the debugging port (lsof -t -i:port -> SIGTERM; win32: psutil cmdline scan for --remote-debugging-port+--user-data-dir match) -> remove the three singleton locks -> launch detached process group -> 0.5s + one-shot startup poll (log stdout/stderr on immediate death) -> 2s settle -> return endpoint. Caller then _verify_cdp_ready GETs /json/version up to 5 times with delay 0.5*1.4^attempt before connect_over_cdp. cleanup: set shutting_down FIRST -> terminate -> poll 10x100ms -> killpg SIGKILL (taskkill /F /T on win32) -> rmtree temp profile.

**Invariant:** (1) Pre-launch cleanup exceptions are NON-FATAL (log + try anyway) - an unkillable stale owner must not wedge startup. (2) shutting_down flips BEFORE any termination signal so the output-draining monitor reports 'terminated normally' instead of alarming. (3) GPU flags are WITHHELD under stealth mode (SwiftShader keeps WebGL alive; disabling it is a headless tell anti-bots detect). (4) Proxy flags pass server URL only - '--proxy-server=http://user:pass@host' is silently ignored by Chromium; credentials ride Playwright context ProxySettings instead. (5) ws:// CDP URLs skip HTTP verification (Playwright owns the handshake).

**Probe:** `tests/browser/` managed-browser suites + `tests/test_cdp_changes.py` (CDP connect/verify behavior)

## Get live surrounding code
**Retrieve:**
```bash
codebase-memory-mcp cli search_graph '{"project": "ext-crawl4ai", "query": "ManagedBrowser start cleanup singleton", "limit": 5}'
```

## Verdict
Adopt the pre-launch hygiene sequence and the escalating shutdown ladder wholesale - both encode battle scars (singleton locks, orphaned port owners, unreaped process groups). Adapt executable lookup and flag lists per platform/target. Keep proxy credentials OUT of --proxy-server; Chromium silently ignores them there - context-level ProxySettings is the working path (persistent context) or CDP-managed auth.
