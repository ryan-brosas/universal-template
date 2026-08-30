<!-- capsule-v2 -->
# CLI daemon reuse ladder — how does a thin CLI get instant responses by reusing a daemon it may have to start?

**Source:** aeo-affiliate-skills MIT `main@ed17ef37bc167b52d9596cbe0292507f001c483d`; Codebase Memory `aeo-affiliate-skills`. **Question:** When every CLI invocation pays process-startup cost, how do you reuse a warm background server without ever blocking longer than a bounded startup budget?

## Three-tier liveness check before spawn
**Path/Symbol:** `tools/src/cli.ts`:`ensureServer` (lines 60–95), helpers `readState` :30–38, `isProcessAlive` :40–47, `healthCheck` :49–58.
**Signature:** `async function ensureServer(): Promise<number>` → port number; `function isProcessAlive(pid: number): boolean`; `async function healthCheck(port: number): Promise<boolean>`.
**Data Shape:** State file `/tmp/affiliate-check.json` holds `{port, pid, token, started}`. `readState()` returns `ServerState | null` — any of missing-file/parse error becomes `null` (tolerant read). Liveness is verified in three escalating tiers before reuse; all constants local: `STARTUP_TIMEOUT = 5000`.

### Decisive source
```ts
const state = readState();
if (state && isProcessAlive(state.pid)) {
  const healthy = await healthCheck(state.port);
  if (healthy) return state.port;
}
// ...spawn...
const proc = Bun.spawn(["bun", "run", serverScript], {
  stdio: ["ignore", "pipe", "pipe"],
  env: { ...process.env },
});
// Wait for server to be ready
const start = Date.now();
while (Date.now() - start < STARTUP_TIMEOUT) {
  const newState = readState();
  if (newState && isProcessAlive(newState.pid)) {
    const healthy = await healthCheck(newState.port);
    if (healthy) return newState.port;
  }
  await new Promise((r) => setTimeout(r, 200));
}
throw new Error("Failed to start affiliate-check server. Is Bun installed?");
```

**Flow:** read state file → pid alive? (signal-0 via `process.kill(pid, 0)` inside try/catch) → HTTP `/health` with `AbortSignal.timeout(1000)` and `.ok` check → reuse port. Otherwise resolve the server script path (see invariant), spawn detached-ish (`stdio ignore/pipe/pipe`, inherited env), then poll state→pid→health every 200 ms until the 5 s budget expires; failure throws an operator-actionable message naming the likely cause ("Is Bun installed?"). The request path itself is one `fetch` with a 10 s timeout returning `response.text()` (`request`, :97–102).
**Invariant:** Never trust a single liveness signal: a stale state file (crashed server) fails tier 2; a live-but-hung pid on the wrong port fails tier 3. The startup poll RE-READS the state file each iteration because the freshly spawned server writes it asynchronously — never cache the pre-spawn `null`.
**Probe:** Repository-owned runner `bun run tests/test-registry-invariants.ts` pins the corpus this tool serves; for this seam the decisive probe is the source pin above plus `grep -n "STARTUP_TIMEOUT" tools/src/cli.ts` → line 21 (`= 5000`) and line 85 (loop bound). Executed GREEN (see verification.md P1/P2).
**Coverage caveat:** none — `tools/src/cli.ts` checked `no_recorded_issue` at generation 2026-08-25T08:24:56Z.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "aeo-affiliate-skills", query: "ensureServer daemon reuse liveness", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the three-tier reuse ladder (state file → signal-0 → short-timeout HTTP health) and the bounded re-read poll loop with an actionable failure string. Adapt the compiled-binary path branch to your packaging: source runs use `dirname(process.argv[1])/server.ts`, but a single-file compile has no sibling script, so the branch keys off `!process.argv[1]?.endsWith(".ts")` and resolves `execPath/../src/server.ts`. Omit the hardcoded `/tmp/affiliate-check.json` path and the unused `token` field as-is (the field is written by the server but never authenticated against — see daemon-idle-self-lifecycle).
