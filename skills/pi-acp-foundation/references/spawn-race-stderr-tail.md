<!-- capsule-v2 -->
# pi RPC spawn race + bounded stderr tail — how do you surface spawn failure deterministically and keep diagnostics without stealing the child's streams?

**Source:** pi-acp-jetbrain MIT `main@1f0524f777c93c51747c26d24f3609c2a4e6731d`; Codebase Memory `pi-acp`. **Question:** How does the pi subprocess transport guarantee ENOENT/EACCES become typed errors instead of late EPIPE noise, and how does it retain diagnostic stderr while ACP clients still receive the raw stream?

## Spawn-ack race + PiRpcSpawnError taxonomy + 200-line tail
**Path/Symbol:** `src/pi-rpc/process.ts` (`PiRpcSpawnError` :5-15, ANSI regex/`stripAnsi` :17-28, `stderrTailLines` :101-104, `onExit` registry :106-109, spawn race in `static spawn` :197-232, `waitForExit` SIGKILL ladder, `request()` timeout+unref). Extends the pass-1 transport capsule with the drift-hardened pieces.
**Signature:** `export class PiRpcSpawnError extends Error { code?: string }`; `stderrTailLines(limit = 40): string[]`; `onExit(handler: (code: number | null, signal: NodeJS.Signals | null) => void): void`.
**Data Shape:** error codes surfaced verbatim from Node spawn errors (`ENOENT`, `EACCES`, …) inside `RequestError.internalError({ code }, message)` at the adapter boundary; stderr tail capped at 200 lines (splice-from-front); request timeout default 30_000ms, `compact`/`export_html` override to 120_000ms; timers always `unref()`'d.

### Decisive source
```ts
// Deterministic spawn-failure surface: race 'spawn' ack vs 'error' BEFORE any RPC.
try { await new Promise<void>((resolve, reject) => {
  const onSpawn = () => { cleanup(); resolve() }
  const onError = (err: Error) => { cleanup(); reject(err) }
  const cleanup = () => { child.off('spawn', onSpawn); child.off('error', onError) }
  child.once('spawn', onSpawn); child.once('error', onError)
}) } catch (error /* -> PiRpcSpawnError with code; ENOENT message names the npm install remedy */)
```

**Flow:** `spawn()` awaits the spawn/error race, mapping ENOENT to a user-actionable message ("Install it via `npm install -g @earendil-works/pi-coding-agent`…"), then runs a best-effort handshake `getState` that pre-creates the session-file parent directory (avoids later export parse errors). Non-JSON stdout lines are captured as ANSI-stripped prelude lines for surfacing at session start. Every pending request carries a timeout timer that deletes its own entry on fire; child exit rejects ALL pendings with a uniform `pi process exited (code=…, signal=…)` error and fires registered exit handlers — the seam `handleProcessExit` uses. `dispose(signal)` is a no-op on an already-dead child; `waitForExit` escalates TERM→(grace)→KILL→500ms→boolean.
**Invariant:** the raw stderr stream is NEVER consumed or paused — the tail observes a copy so clients capturing stderr still get everything; exit-handler invocation and pending rejection happen exactly once per process lifecycle; no timer outlives its request (unref + explicit clearTimeout on settle).
**Probe:** `npx tsx --test test/unit/pi-rpc-process.test.ts` (transport semantics incl. prelude capture and timeout paths) — executed GREEN at pin.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-acp", query: "PiRpcSpawnError stderrTailLines stripAnsi waitForExit", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the spawn-ack race as the ONLY place spawn failures are interpreted, the observed-not-consumed stderr tail, and once-only exit fan-out to pending requests. Adapt the remedy text and arg shape to your agent CLI. Omit the Windows shell branch if you are POSIX-only (see win-cmd-shell-spawn). Direct tests executed green at the pin.
