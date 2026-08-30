<!-- capsule-v2 -->
# Harness daemon lifecycle — how does a CLI lazily start, version-check, soft-restart, and quit a shared server without orphaning workers?

**Source:** pi-messenger-swarm MIT `main@6fe429a4b74ae276a621bb72910d7926fb6b3104`; Codebase Memory `mnt-hdd-utopia-inspo-external-ext-pi-messenger-swarm`. **Question:** What is the full daemon choreography a porter must reproduce?

## Lazy spawn → version gate → preserve-spawns quit semantics
**Path/Symbol:** `harness/cli.ts:startServer` (:314-376), version check (:587-610), `--restart` (:538-558); `harness/server.ts:/restart` (:643-655), `/quit` (:662-687), signal handler (:712-725), uncaught handlers (:733-743).
**Signature:** `startServer(): Promise<boolean>` polls `/health` up to 100×100ms after detached+unref'd spawn.
**Data Shape:** env allowlist into the daemon: only `PI_MESSENGER_GLOBAL` passes through; `PI_MESSENGER_CWD`/`PI_MESSENGER_DIR` are FORCE-set to project root; `PI_MESSENGER_CHANNEL` is deliberately STRIPPED.

### Decisive source
```ts
// IMPORTANT: The restart uses x-preserve-spawns so the old server persists running
// spawn state to disk and exits WITHOUT killing spawned agent processes.
await httpPost(`${BASE_URL}/quit`, '', { 'x-preserve-spawns': '1' });
```
```ts
process.on('uncaughtException', (err) => {
  serverLog(`uncaughtException: ...`);
  // Don't exit — keep serving. ... better to log and continue than to kill all in-progress work.
});
```

**Flow:** every subcommand first ensures the daemon (health probe → detached spawn → poll). Before dispatching, CLI compares its version against `/health.version` and on mismatch quits-with-preserve then starts fresh. `/quit` WITHOUT the header stops all spawns, waits 2s, force-kills; WITH it, persists runtimes and exits in 500ms leaving workers alive. Signals always preserve spawns (version-restart assumption).
**Invariant:** Stripping PI_MESSENGER_CHANNEL from the daemon env is load-bearing: it is a PER-REQUEST hint forwarded as `x-messenger-channel`, and baking it into the long-lived server would pin EVERY subsequent request from all agents to that one channel. Log-and-continue error policy trades crash-safety for worker safety — porters wanting fail-fast will orphan every spawned agent.
**Probe:** direct tests `tests/swarm/soft-restart.test.ts::config loaded before restart reflects the original value` (:51) + dirs-resolution cases (:89+); `grep -o "x-preserve-spawns" harness/cli.ts | wc -l` (=4: two POSTs + two comments) and on harness/server.ts (=3); `grep -c "_strip, ...serverEnv" harness/cli.ts` (=1).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-external-ext-pi-messenger-swarm", query: "startServer preserve-spawns restart persistRuntimes uncaughtException", limit: 6 });
```

## Verdict
Adopt lazy-daemon + version-gate + preserve-vs-kill quit duality + strip-per-request-env rules; adapt port/log paths; omit the tsx fallback if you ship compiled only.
