<!-- capsule-v2 -->
# Browser close idempotence — how does close() stay safe when called twice or concurrently, and fan death out to every context and download?

**Source:** playwright (microsoft/playwright) Apache-2.0 `main@d4e1023f6c03a8dced50eb3db88c2217e7c1a86a`; Codebase Memory `playwright`. **Question:** When a session object's shutdown may be triggered by user code, peer death, AND a second concurrent caller, how do you make the entry point idempotent while still letting late callers await actual death?

## `_startedClosing` latch + Disconnected await
**Path/Symbol:** `packages/playwright-core/src/server/browser.ts:Browser._close` (lines 189-198), `didClose` (173-183), `close`/`killForTests` (185-204); `BrowserProcess` interface (41-46).
**Signature:** `async close(progress: Progress, options: { reason?: string })`; `protected didClose(): void`; interface `BrowserProcess { onclose?(exitCode, signal); process?: ChildProcess; kill(): Promise<void>; close(): Promise<void> }`.
**Data Shape:** `_startedClosing: boolean` latch; `_closeReason` records WHY for error surfaces; death reaches the server as `browserProcess.onclose(exitCode, signal)` wired in `BrowserType._launchProcess` (`browser.ts` never touches the ChildProcess directly).

### Decisive source
```ts
private async _close(options: { reason?: string }) {
  if (!this._startedClosing) {
    if (options.reason) this._closeReason = options.reason;
    this._startedClosing = true;
    await this.options.browserProcess.close();
  }
  if (this.isConnected())
    await new Promise(x => this.once(Browser.Events.Disconnected, x));
}

protected didClose() {
  for (const context of this.contexts()) context.browserClosed();
  if (this._defaultContext) this._defaultContext.browserClosed();
  for (const download of this._downloads.values())
    download.artifact.reportFinished(new TargetClosedError(undefined));
  this.stopServer(nullProgress).catch(() => {});
  this.emit(Browser.Events.Disconnected);
  this.instrumentation.onBrowserClose(this);
}
```

**Flow:** first close() wins the latch and drives `browserProcess.close()` (the graceful-close ladder capsule); concurrent/repeat callers skip straight to awaiting `Disconnected`, which fires exactly once from `didClose()` when the process's `'close'` event lands. `didClose` fans out synchronously: mark every context closed → fail every in-flight download with `TargetClosedError` → stop the remote server (fire-and-forget with swallowed error) → emit → instrumentation.
**Invariant:** The latch is set BEFORE any await inside the guarded block, so two simultaneous closes cannot both drive the ladder; and `Disconnected` must be emitted exactly once, after all fan-out, so awaiters resume only when contexts/downloads are already reconciled. Note `killForTests` uses the same await-Disconnected tail but forces `kill()` instead of the graceful ladder.
**Probe:** `tests/library/browsertype-launch.spec.ts:113-120` (`should be callable twice`: `Promise.all([close(), close()])` then a third close) and :104-111 (`should fire close event for all contexts`) pin both halves of the contract.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "playwright", query: "startedClosing didClose disconnected browser close", limit: 10 });
// resolves Browser._close / didClose / killForTests (server/browser.ts 173-205)
```

## Verdict
Adopt set-latch-before-await idempotence, "late callers await the single death event", reason-carrying close, and synchronous didClose fan-out (contexts → downloads → server → event) as portable contracts. Adapt what fan-out means for your object graph and whether your transport needs the fire-and-forget server stop. Omit the test-only kill variant unless you have an equivalent harness need.
