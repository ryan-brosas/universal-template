<!-- capsule-v2 -->
# Daemon idle self-lifecycle — how does the daemon own its port, state file, and idle shutdown without leaking either?

**Source:** aeo-affiliate-skills MIT `main@ed17ef37bc167b52d9596cbe0292507f001c483d`; Codebase Memory `aeo-affiliate-skills`. **Question:** How does an unattended localhost server pick a free port, publish discoverable state, shut itself down when forgotten, and clean up on every exit path?

## Probe-bind port scan, state publication, idle self-exit
**Path/Symbol:** `tools/src/server.ts`:`findPort` (238–249), `main` (251–285), `resetIdleTimer` (27–35), `cleanup` (230–236), `/stop` branch of `handleRequest` (74–81).
**Signature:** `async function findPort(): Promise<number>`; `async function main(): Promise<void>`; `function resetIdleTimer(): void`; `function cleanup(): void`.
**Data Shape:** Constants `PORT_RANGE_START=9500`, `PORT_RANGE_END=9510`, `IDLE_TIMEOUT_MS = 30*60*1000`, `STATE_FILE="/tmp/affiliate-check.json"`. State written: `{port, pid, token, started}` pretty-printed JSON. Module singletons `lastActivity`, `startTime`, `idleTimer`.

### Decisive source
```ts
async function findPort(): Promise<number> {
  for (let port = PORT_RANGE_START; port <= PORT_RANGE_END; port++) {
    try {
      const server = Bun.serve({ port, fetch: () => new Response("") });
      server.stop(true);
      return port;
    } catch { continue; }
  }
  throw new Error(`No available port in range ${PORT_RANGE_START}-${PORT_RANGE_END}`);
}

function resetIdleTimer() {
  lastActivity = Date.now();
  clearTimeout(idleTimer);
  idleTimer = setTimeout(() => {
    console.log("[affiliate-check] Idle timeout — shutting down");
    cleanup();
    process.exit(0);
  }, IDLE_TIMEOUT_MS);
}
```

And the two exit-path details that prevent the classic wrong ports:

```ts
// /stop — answer first, die later so the response flushes:
if (path === "/stop") {
  setTimeout(() => { cleanup(); process.exit(0); }, 100);
  return new Response("Shutting down.\n", ...);
}

// handleRequest line 52 — the FIRST statement of every request:
resetIdleTimer();
```

**Flow:** `main` scans the fixed range by transient probe-bind (serve→`stop(true)`→return first bindable; exhausted range throws) → binds the real server → writes the state file the CLI's reuse ladder reads → arms the idle timer → installs SIGINT/SIGTERM handlers that call `cleanup()` then exit. Every request re-arms the timer as its first action, including `/health` and `/status`. `cleanup()` clears the timer and unlinks the state file inside try/catch-swallow.
**Invariant:** All four exit paths (idle timeout, SIGINT, SIGTERM, `/stop`) funnel through `cleanup()` so the state file never outlives its server — but note it is best-effort (`unlinkSync` in swallow-errors): a SIGKILL leaves a stale file, which is exactly why the CLI's tier-2/3 liveness checks exist. The idle timer resetting on `/health` means health-based monitoring keeps the daemon alive indefinitely — adopt deliberately if you add monitoring.
**Probe:** Source pins executed via grep: `grep -n "IDLE_TIMEOUT_MS" tools/src/server.ts` → :19 (30-min constant), :34 (timer arm); `grep -n "process.exit(0)" tools/src/server.ts` → :33 (idle), :78 (/stop deferred), :279/:283 (signals). Deterministic battery recorded in verification.md P3–P5.
**Coverage caveat:** none — `tools/src/server.ts` checked `no_recorded_issue` at generation 2026-08-25T08:24:56Z.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "aeo-affiliate-skills", query: "findPort resetIdleTimer cleanup state file", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt probe-bind port selection over a small fixed range with an exhaustion error, state-file publication as the discovery contract, one shared cleanup for every exit path, and the deferred-exit trick for graceful `/stop` responses. Adapt the idle-reset placement consciously: resetting at the top of request handling makes any traffic (even monitoring) keep-alive. Omit the `token = crypto.randomUUID()` field unless you also enforce it — here it is written but never checked, i.e., no auth on the loopback listener.
