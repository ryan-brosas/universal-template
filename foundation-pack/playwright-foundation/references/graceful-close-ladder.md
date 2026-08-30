<!-- capsule-v2 -->
# Graceful-close ladder — how does close degrade from a polite protocol message to force-kill without hanging or leaving zombies?

**Source:** playwright (microsoft/playwright) Apache-2.0 `main@d4e1023f6c03a8dced50eb3db88c2217e7c1a86a`; Codebase Memory `playwright`. **Question:** When shutting down a peer process, how do you order protocol-level close, timeout, reentrancy (second Ctrl+C / double close), and force-kill so every path still awaits actual death and temp-dir cleanup?

## closeOrKill + reentrancy-aware gracefullyClose
**Path/Symbol:** `packages/utils/processLauncher.ts:gracefullyClose` (lines 206-223); `packages/playwright-core/src/server/browserType.ts:_launchProcess` → `closeOrKill` (lines 245-263).
**Signature:** `gracefullyClose(): Promise<void>` (closure over the spawn); `closeOrKill(timeout): Promise<void>`; `browserProcess.close = () => closeOrKill(__testHookBrowserCloseTimeout || DEFAULT_PLAYWRIGHT_TIMEOUT /* 30s */)`.
**Data Shape:** `attemptToGracefullyClose()` may **reject** to signal "polite close impossible" (e.g. no transport yet). `kill()` resolves only after the process died AND cleanup finished (`waitForCleanup`).

### Decisive source
```ts
let gracefullyClosing = false;
async function gracefullyClose(): Promise<void> {
  // We keep listeners until we are done ... This might introduce
  // reentrancy ... In this case, let's forcefully kill the process.
  if (gracefullyClosing) {
    killProcess();
    await waitForCleanup;  // Ensure the process is dead and we have cleaned up.
    return;
  }
  gracefullyClosing = true;
  await options.attemptToGracefullyClose().catch(() => killProcess());
  await waitForCleanup;  // Ensure the process is dead and we have cleaned up.
}
// browserType.ts:
await Promise.race([gracefullyClose(), new Promise((res, rej) => timer = setTimeout(rej, timeout))]);
// catch -> await kill().catch(...); finally clearTimeout(timer)
```
Engine grace messages: Chromium sends `{ method: 'Browser.close', id: kBrowserCloseMessageId }` (chromium.ts:244-248), WebKit sends `Playwright.close` (webkit.ts:96-99), BiDi Firefox opens a session first if none exists then sends `browser.close` (bidiFirefox.ts:79-93). The launching connection deliberately swallows that reply — `crConnection._onMessage` returns early on `message.id === kBrowserCloseMessageId` (crConnection.ts:80-81).

**Flow:** close requested → race(polite protocol close vs timeout) → polite attempt rejects/times out → sync `killProcess()` (SIGKILL tree) → `'close'` event fires → async temp-dir cleanup resolves `waitForCleanup` → close() returns. A second concurrent close sees `gracefullyClosing === true` and goes straight to kill+wait.
**Invariant:** Every exit path must end awaiting `waitForCleanup` — no caller of close/kill may observe "closed" while temp dirs exist or the pid lives. Listeners stay installed during async closing specifically so mid-close SIGINT/'exit' cannot orphan the process.
**Probe:** `tests/library/browsertype-launch.spec.ts:113-120` (`should be callable twice`) pins concurrent + repeated `browser.close()` resolving cleanly.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "playwright", query: "attemptToGracefullyCloseBrowser kBrowserCloseMessageId", limit: 10 });
// resolves all four engine variants incl. BidiFirefox._attemptToGracefullyCloseBrowser (bidiFirefox.ts 79-93)
```

## Verdict
Adopt the ladder ordering (protocol message → timeout race → group SIGKILL → await death+cleanup) and the reentrant-second-call-means-force-kill rule as portable. Adapt which "polite" wire message your peer understands and the 30s default. Omit the per-engine message ids. Caveat: the kBrowserCloseMessageId ignore contract is verified in crConnection/bidiConnection/wk/ff `_onMessage` sources but has no dedicated unit test.
