<!-- capsule-v2 -->
# Desktop boot-splash launch chain — how does an Electron shell start a local full stack, keep the user informed, and still shut every detached child down?

**Source:** OpenHands / All-Hands-AI (MIT) `main@8511fff62d3084587cda1add483fe5ea9c8bfd7e`; Codebase Memory `openhands`. **Question:** How should a desktop shell that spawns a Python+Node backend stack handle PATH injection, two-stage readiness, a startup-log splash, and cross-platform cleanup of detached process groups?

## Splash window over a staged backend boot
**Path/Symbol:** `electron/main.mjs` (`injectBundledUv` :94–124, `injectBundledNode` :170–226, `waitForUrl` :235–247, `waitForAgentServer` :260–283, boot-log buffer :439–508, `startStack` :613–649, `before-quit` :746–768), `electron/preload.cjs` (31 L), `bin/agent-canvas.mjs` (:125–159).
**Signature:** `async function waitForAgentServer(url = "http://localhost:8000/server_info", timeoutMs = 10 * 60_000, intervalMs = 1_000)`; `app.on("before-quit", (event) => { … event.preventDefault(); … })`.
**Data Shape:** Boot log entries `{name, line, level}` in a bounded 2000-line buffer; IPC channels `boot-log:batch|fatal|set-expanded|copy|quit` all guarded by `isLoadingWinEvent(event)`.

### Decisive source
```ts
// Only 200 is success here. 502 from ingress means the upstream agent
// server isn't bound yet; 401 means auth is required and the bundled
// key didn't reach us — we still treat that as "the agent server is
// up", because the proxy got a real HTTP response from it.
if (res.status === 200 || res.status === 401) return;
```
```ts
// Windows has no real POSIX signals: process.kill(pid, "SIGTERM") would
// terminate this process WITHOUT running the "SIGTERM" listener, skipping
// cleanup and orphaning the children on ports 8000/18000/18001 …
if (!process.emit("SIGTERM")) app.exit(0);
```

**Flow:** `app.whenReady` → inject bundled uv/node onto PATH → `uvxAvailable()` dialog-or-die → create frameless loading window → `startStack()` (dynamic-imports `scripts/dev-with-automation.mjs`, `staticMode:true`, 10-min agent-server budget, `onServiceLog` tee) → stage 1 `waitForUrl` (<500 = ingress bound) → stage 2 `waitForAgentServer` (end-to-end 200-or-401) → destroy splash, show+maximize main window at `http://localhost:8000`. Failure keeps the splash open expanded with Copy logs / Quit; only when the splash is already gone does it fall back to `dialog.showErrorBox` + recent-error tail.
**Invariant:** Readiness has TWO distinct bars — proxy bound (`<500`) and upstream actually serving (`200`/`401` end-to-end) — and opening the main window requires the stricter one. Cleanup must run the registered SIGTERM handler even on Windows (`process.emit`, not `process.kill`) with a 6 s force-exit safety net; the second `before-quit` sees `cleanupStarted` and allows exit.
**Probe:** executed live: `node bin/agent-canvas.mjs --version` → `1.15.0`, exit 0; `--frontend-only --backend-only` → exit 1 `"Error: --frontend-only and --backend-only cannot be used together"`. Direct-test boundary: `__tests__/scripts/dev-with-automation.test.ts` (no dedicated electron-main unit test exists — recorded caveat): busy ingress port throws rather than falling back (:347-364); SIGHUP cleans detached services and releases the port (:856-952).

### Secondary invariants worth porting
- Bundled-runtime injection: chmod 0o755 what electron-builder stripped; PREPENDING a half-copied npm bundle SHADOWS the user's working npm — warn loudly but still inject `node`. Electron-as-Node was rejected: stdio JSON-RPC MCP servers die under its stdin/stdout semantics.
- Log hygiene for non-TTY children: strip ANSI CSI and collapse `\r` progress frames to the final frame (`sanitizeLogLine` :457–464); buffer replay on `did-finish-load` because IPC receivers don't exist before page load.
- `preload.cjs` is CommonJS on purpose (sandboxed preloads can't use ESM); the status headline intentionally bypasses it via `executeJavaScript` → `window.__setLoadingStatus`.
- CLI flag validation (mutual exclusion, build-dir existence unless `--backend-only`) precedes any dynamic import.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openhands", query: "electron main window ipc preload", limit: 10, fields: ["lines", "signature"] });
// → createMainWindow :354-426, appendBootLog :466-476, sanitizeLogLine :457-464 …
```

## Verdict
Adopt the two-bar readiness ladder, the emit-not-kill Windows shutdown dance, the bounded-replay boot log, and validate-before-import CLI ordering. Adapt ports/paths/uv specifics to your stack. Omit macOS dock icon handling and NSIS AppUserModelId details unless shipping a Windows installer. Coverage caveat: no dedicated electron/main.mjs test exists (documented; deterministic probes + adjacent suite stand in).
