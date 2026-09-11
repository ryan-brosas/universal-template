<!-- capsule-v2 -->
# Process-signal handler refcount — how do N concurrently launched processes share SIGINT/SIGTERM/exit handlers and uninstall them exactly when the last one dies?

**Source:** playwright (microsoft/playwright) Apache-2.0 `main@d4e1023f6c03a8dced50eb3db88c2217e7c1a86a`; Codebase Memory `playwright`. **Question:** When each launched process wants Ctrl+C to close browsers gracefully, how do you install process-level signal handlers once for all of them — and remove them at exactly the right moment?

## Set-sized refcount + two-press SIGINT latch
**Path/Symbol:** `packages/utils/processLauncher.ts` lines 51-129 (`gracefullyCloseSet`, `killSet`, `addProcessHandlerIfNeeded`, `removeProcessHandlersIfNeeded`, `sigintHandler`, `gracefullyProcessExitDoNotHang`).
**Signature:** `addProcessHandlerIfNeeded(name: 'exit'|'SIGINT'|'SIGTERM'|'SIGHUP')`; `removeProcessHandlersIfNeeded()`; `gracefullyProcessExitDoNotHang(code: number, onExit?: () => Promise<void>)`.
**Data Shape:** Module-level `installedHandlers: Set<name>` plus two per-process membership sets; "refcount" is literally `killSet.size`.

### Decisive source
```ts
function removeProcessHandlersIfNeeded() {
  if (killSet.size) return;              // other browsers still alive -> keep handlers
  for (const handler of installedHandlers) process.off(handler, processHandlers[handler]);
  installedHandlers.clear();
}
let sigintHandlerCalled = false;
function sigintHandler() {
  if (sigintHandlerCalled) {             // second Ctrl+C: stop waiting
    process.off('SIGINT', sigintHandler);
    for (const kill of killSet) kill();  // immediate force-kill, exit 130
    exitWithCode130();
  } else {
    sigintHandlerCalled = true;
    gracefullyCloseAll().then(() => exitWithCode130());
  }
}
```
`exitHandler` iterates `killSet` **synchronously** (process 'exit' handlers cannot await) — this is why `killProcess` must be sync. `gracefullyProcessExitDoNotHang` starts a 30s forced `process.exit(code)` timer and races it against `gracefullyCloseAll()` so a hung browser can't hang shutdown.

**Flow:** first launch installs handlers once → every launch adds its closures to the sets → any close/kill removes its closures → when `killSet` empties, ALL handlers are uninstalled in one sweep → SIGINT follows graceful-then-forced ladder keyed by the module-level `sigintHandlerCalled` latch.
**Invariant:** Handlers must be removed only when zero live processes remain (never per-process), or surviving browsers lose their Ctrl+C/exit safety net; the second-SIGINT path must bypass grace entirely to escape a stalled graceful close.
**Probe:** No dedicated upstream unit test exists next to `processLauncher.ts` (only index.js in that package); behavior is pinned indirectly by library suites exercising Ctrl+C during launches. Coverage caveat recorded in-capsule.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "playwright", query: "addProcessHandlerIfNeeded removeProcessHandlers sigint", limit: 10 });
// resolves addProcessHandlerIfNeeded / removeProcessHandlersIfNeeded / launchProcess callers in server/browserType.ts
```

## Verdict
Adopt set-membership-as-refcount for shared process signal handlers, the two-press SIGINT ladder, and the 30s do-not-hang forced exit as portable contracts. Adapt signal names/exit codes to your platform and whether your tests need an async grace window (`isUnderTest()` branch). Omit Playwright's specific exit code 130 semantics if your host defines its own.
