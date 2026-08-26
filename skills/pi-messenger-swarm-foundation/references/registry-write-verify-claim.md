<!-- capsule-v2 -->
# Registry write-verify-claim — how do agents claim unique names with no lock server?

**Source:** pi-messenger-swarm MIT `main@6fe429a4b74ae276a621bb72910d7926fb6b3104`; Codebase Memory `mnt-hdd-utopia-inspo-external-ext-pi-messenger-swarm`. **Question:** How is a registry filename used as a mutex for agent identity without any locking protocol?

## Write → read-back PID verify → unlink on loss
**Path/Symbol:** `store/registration.ts:register` (:34-206), `store/registration.ts:renameAgent` (:362-469), `store/agents.ts:findAvailableName` (:188-216).
**Signature:** `register(state, dirs, ctx, nameTheme?): boolean`; `renameAgent(...): RenameResult` (error union incl. `'race_lost'`).
**Data Shape:** one JSON file per agent at `<base>/registry/<name>.json` holding `{name, pid, sessionId, cwd, model, startedAt, reservations?, joinedChannels, ...}`. Liveness = `isProcessAlive(pid)` (`process.kill(pid,0)`).

### Decisive source
```ts
fs.writeFileSync(regPath, JSON.stringify(registration, null, 2));
// ...
let verified = false;
try {
  const written: AgentRegistration = JSON.parse(fs.readFileSync(regPath, 'utf-8'));
  verified = written.pid === effectivePid;   // read-back IS the claim check
} catch { verifyError = true; }
if (!verified /* && verifyError */) {
  // best-effort cleanup: unlink only if content still matches OUR pid
}
if (isExplicitName) return false;  // explicit-name conflicts NEVER retry
invalidateAgentsCache();           // auto-name loop retries with next suffix
```

**Flow:** pre-check existing file (alive foreign pid ⇒ refuse) → delete stale own file → write new registration → read back and compare pid → verified = claimed; read-back failure triggers cleanup-unlink and either retry-with-suffix (`findAvailableName` scans `<base>2..99`) or hard fail.
**Invariant:** The read-back comparison is the entire concurrency story — last-writer-wins on the file, but only the writer whose pid survives the round-trip keeps the identity. Explicit names never auto-rename (user intent wins); generated names retry. Dead-pid files are treated as free real estate everywhere (`getActiveAgents` even unlinks them lazily).
**Probe:** direct tests `tests/store.test.ts::channel-aware registration > creates phrase-based session channels...` + `tests/swarm/project-isolation.test.ts::should use project-scoped registry by default`; `grep -c "verified = written.pid === effectivePid" store/registration.ts` (=2 — the SAME verify idiom in BOTH register :165 and renameAgent :434); `grep -c "race_lost" store/registration.ts` (=2: union member + return).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-external-ext-pi-messenger-swarm", query: "register renameAgent findAvailableName isProcessAlive", limit: 8 });
```

## Verdict
Adopt write-readback-verify as a portable lockless name-claim primitive and dead-pid-as-garbage-collection semantics; adapt the registry dir/name grammar to your host; omit the UI notify branches (`ctx.hasUI`) when headless.
