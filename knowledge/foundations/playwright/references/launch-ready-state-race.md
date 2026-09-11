<!-- capsule-v2 -->
# Launch readiness race & startup-log rewrite — how does launch fail fast and readably when the browser process dies before it is ready?

**Source:** playwright (microsoft/playwright) Apache-2.0 `main@d4e1023f6c03a8dced50eb3db88c2217e7c1a86a`; Codebase Memory `playwright`. **Question:** While waiting for a spawned peer to signal readiness, how do you unblock instantly if it dies first, and how do you turn its raw startup spew into an actionable error?

## exitPromise raced against ready-state + RecentLogsCollector rewrite
**Path/Symbol:** `packages/playwright-core/src/server/browserType.ts:_launchProcess` (lines 199-285, readiness race 264-284); `_innerLaunchWithRetries` (95-107); `_innerLaunch` error containment (144-147); `packages/playwright-core/src/server/chromium/chromium.ts:doRewriteStartupLog` (222-238).
**Signature:** `_launchProcess(...): Promise<{ browserProcess: BrowserProcess, artifactsDir, userDataDir, transport: ConnectionTransport, wsEndpoint? }>`; `onExit: (exitCode, signal) => void` resolves a `ManualPromise` (`exitPromise`).
**Data Shape:** `RecentLogsCollector` keeps the tail of `<launching>`/`<launched> pid=`/stdout/stderr lines emitted through the launch log callback; per-engine subclasses override `waitForReadyState` (default resolves immediately), `supportsPipeTransport`, `doRewriteStartupLog`.

### Decisive source
```ts
const { wsEndpoint } = await progress.race([
  this.waitForReadyState(options, browserLogsCollector),
  exitPromise.then(() => ({ wsEndpoint: undefined })),   // premature death unblocks launch
]);
if (exitPromise.isDone()) {
  const log = helper.formatBrowserLogs(browserLogsCollector.recentLogs());
  throw new Error(`Failed to launch the browser process.\nBrowser logs:\n${this.doRewriteStartupLog(log)}`);
}
if (!this.supportsPipeTransport(options))
  transport = await WebSocketTransport.connect(progress, wsEndpoint!);
else
  transport = new PipeTransport(stdio[3], stdio[4]);     // fd 3/4 protocol pipe
```
Chromium's rewrite detects `'Missing X server'` → ASCII-boxed "No X server running" guidance, and Chromium-source sandbox strings (`crbug.com/357670`, `No usable sandbox!`) → actionable "use `chromiumSandbox: false`" advice. Error containment ladders: `_innerLaunch` catch closes the just-spawned browserProcess; `_launchProcess` catch runs `closeOrKill(DEFAULT_PLAYWRIGHT_TIMEOUT)`; `_innerLaunchWithRetries` retries **exactly once** when the error message contains `'Inconsistency detected by ld.so'` (glibc constructor race, microsoft/playwright#5214).

**Flow:** prepare temp dirs + args → spawn via launchProcess → race(readyState vs exit) → death wins ⇒ throw with rewritten captured logs; ready wins ⇒ build Pipe/WebSocket transport. Any later failure in `_innerLaunch` (transport handshake, default-context load) still closes the process before propagating.
**Invariant:** No launch failure path may leave the spawned process or its temp dirs alive — every catch on the way out funnels into `browserProcess.close()`/`closeOrKill`; and a dead-peer launch must fail within one event-loop turn of exit, not at full timeout.
**Probe:** `tests/library/browsertype-launch.spec.ts:78-96` pins that a timed-out launch reports `browserType.launch: Timeout 5000ms exceeded.` including `<launching>` and `<launched> pid=` from the captured log; :64-70 pins immediate-death launches surfacing `Browser logs:`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "playwright", query: "waitForReadyState exitPromise launch browser logs", limit: 10 });
// resolves BrowserType._launchProcess (server/browserType.ts 199-285), doRewriteStartupLog overrides ×5 engines
```

## Verdict
Adopt racing a death-promise against readiness instead of waiting out the timeout, capturing a rolling startup-log tail for the error, rewriting known vendor failures into actionable text, single-retry only for a named transient, and catch-path close-everything as portable contracts. Adapt the ready-state predicate, rewrite rules, and retry fingerprint to your peer. Omit Playwright's test-hook escape hatches (`__testHook*`).
