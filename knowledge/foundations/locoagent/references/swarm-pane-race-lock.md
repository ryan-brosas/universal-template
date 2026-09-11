<!-- capsule-v2 -->
# Pane-creation race lock — how do parallel teammate spawns avoid interleaving tmux layout commands?

**Source:** locoagent (Claude Code CLI fork, MIT), rev `c01bb3f`; Codebase Memory `locoagent`. **Question:** what synchronizes concurrent `createTeammatePaneInSwarmView` calls so the first-teammate split and pane-count reads stay coherent?

## Promise-chained mutex (identical twin in both pane backends)
**Path/Symbol:** `src/utils/swarm/backends/TmuxBackend.ts:acquirePaneCreationLock` (:43-53), `paneCreationLock` (:29), `PANE_SHELL_INIT_DELAY_MS` (:33), `waitForPaneShellReady` (:35-37); `src/utils/swarm/backends/ITermBackend.ts:acquirePaneCreationLock` (:21-31).
**Signature:** `acquirePaneCreationLock(): Promise<() => void>` — returns a release function that MUST be called (callers use try/finally).
**Data Shape:** module-level `let paneCreationLock: Promise<void> = Promise.resolve()` — the chain head.

### Decisive source
```ts
function acquirePaneCreationLock(): Promise<() => void> {
  let release: () => void
  const newLock = new Promise<void>(resolve => { release = resolve })
  const previousLock = paneCreationLock
  paneCreationLock = newLock
  return previousLock.then(() => release!)
}
```

**Flow:** caller awaits `previousLock.then(() => release)` — i.e., it resolves only after every earlier holder released → whole create operation (detect environment, split window, color/title, rebalance) runs under try/finally release → after creation, `waitForPaneShellReady()` sleeps 200ms "enough for most shell configurations including slow ones like starship/oh-my-zsh" BEFORE returning, so the immediate next `sendCommandToPane` lands in an interactive shell rather than being eaten during rc-file loading.
**Invariant:** FIFO ordering by construction; release must be in finally or one throw deadlocks all future spawns; shell-init delay is part of the create contract, not a UI nicety; the SAME pattern is duplicated verbatim in both backends — porters must replicate it in any new backend.
**Probe:** coverage caveat (no direct tests). Deterministic probes: `grep -n 'starship/oh-my-zsh' src/utils/swarm/backends/TmuxBackend.ts` (:32); `grep -c 'acquirePaneCreationLock' src/utils/swarm/backends/ITermBackend.ts` (≥3).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "acquirePaneCreationLock waitForPaneShellReady createTeammatePaneInSwarmView", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt promise-chain mutexes for serialized external-tool mutation sequences plus post-create readiness delays; adapt delay constants to your shells; omit nothing else.
