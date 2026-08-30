<!-- capsule-v2 -->
# Crash-and-shutdown contract — how does a stdio adapter die without orphaning children or looking idle?

**Source:** pi-acp-jetbrain MIT `main@1f0524f777c93c51747c26d24f3609c2a4e6731d`; Codebase Memory `pi-acp`. **Question:** How must an ACP/stdio agent adapter handle uncaught exceptions, unhandled rejections, and client disconnect so a dead adapter never masquerades as an idle session and no pi/MCP child outlives it?

## exitOnCrash + awaited disposeAll shutdown
**Path/Symbol:** `src/exit-on-crash.ts` whole file (`exitOnCrash` :8-33) + `src/index.ts` (:53-109: retained `activeAgent`, `shutdown()`, signal wiring, `uncaughtException`/`unhandledRejection` handlers) + `SessionManager.disposeAll` in `src/acp/session.ts` (:158-161).
**Signature:** `export function exitOnCrash(kind: string, detail: unknown, dispose: (() => Promise<void> | void) | null, exit: (code: number) => void = code => process.exit(code), timeoutMs = 2_000): void`; `async dispose(): Promise<void>` on the agent (awaited by shutdown).
**Data Shape:** stderr line format `pi-acp-jetbrain: <kind>: <stack-or-String(detail)>\n`; exit code always 1 on crash; 2s disposal budget before forced exit.

### Decisive source
```ts
const timer = setTimeout(() => exit(1), timeoutMs)
timer.unref?.()
if (!dispose) { clearTimeout(timer); return exit(1) }
void Promise.resolve(dispose())
  .catch(() => undefined)
  .finally(() => { clearTimeout(timer); exit(1) })
```

**Flow:** crash handlers capture the singleton agent (the SDK's AgentSideConnection hides its handler instance, so construction retains it via `activeAgent = new PiAcpAgent(conn)`), null it FIRST (prevents double-dispose from a second event), then log + best-effort dispose owned children + exit nonzero — the comment is the contract: "a dead-but-zero adapter would look like an idle session". Graceful stdin-end/SIGINT/SIGTERM path runs `await activeAgent.dispose()` which now AWAITS `Promise.all(sessions.map(closeSession))` (was fire-and-forget `void closeSession`) so pi subprocess teardown completes before `process.exit(0)`; a `shuttingDown` latch makes it idempotent. Testable shape: `exit` and `timeoutMs` injectable; entrypoint-shutdown test spawns a REAL child pi and asserts closing stdin waits for its termination.
**Invariant:** crash exit code MUST be nonzero; dispose errors are swallowed (`.catch(() => undefined)`) because "the exit below is authoritative"; the timer is `unref`'d so a fast dispose isn't held hostage by the timeout.
**Probe:** `npx tsx --test test/unit/exit-on-crash.test.ts test/unit/entrypoint-shutdown.test.ts` (both executed GREEN at pin; entrypoint test drives a real child process).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-acp", query: "exitOnCrash shutdown activeAgent dispose", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt nonzero-exit crash semantics with bounded best-effort child disposal, handler-instance retention for SDKs that hide it, and awaited-all session teardown on graceful paths. Adapt the brand prefix and exit codes to your host. Omit nothing — this is small and fully portable. Both direct tests executed green at the pin.
