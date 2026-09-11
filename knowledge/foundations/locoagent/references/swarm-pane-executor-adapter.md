<!-- capsule-v2 -->
# PaneBackendExecutor adapter — how do tmux/iTerm2 backends satisfy the same lifecycle contract as in-process?

**Source:** locoagent (Claude Code CLI fork, MIT), rev `c01bb3f`; Codebase Memory `locoagent`. **Question:** what does adapting a raw PaneBackend into a TeammateExecutor add beyond delegation?

## Adapter adds identity flags, tracking map, cleanup, mailbox prompt
**Path/Symbol:** `src/utils/swarm/backends/PaneBackendExecutor.ts:spawn` (:79-209), `terminate` (:252-290), `kill` (:295-320), `isActive` (:329-344), cleanup registration (:163-175).
**Signature:** `new PaneBackendExecutor(backend: PaneBackend)` — wraps; `setContext(context)` required before spawn.
**Data Shape:** `spawnedTeammates: Map<agentId, { paneId, insideTmux }>`; `cleanupRegistered` one-shot flag.

### Decisive source
```ts
// Build the command to spawn Claude Code with teammate identity
const spawnCommand = `cd ${quote([workingDir])} && env ${envStr} ${quote([binaryPath])} ${teammateArgs}${flagsStr}`
// Send the command to the new pane
// Use swarm socket when running outside tmux (external swarm session)
await this.backend.sendCommandToPane(paneId, spawnCommand, !insideTmux)
```
```ts
// For now, assume active if we have a record of it
// A more robust check would query the backend for pane existence
// but that would require adding a new method to PaneBackend
return true
```

**Flow:** spawn: assign color (round-robin via teammateLayoutManager) → backend.createTeammatePaneInSwarmView → enable border status on FIRST teammate when inside tmux → build `cd && env ... binary --agent-id --agent-name --team-name --agent-color --parent-session-id` command with inherited flags/env (spawnUtils) → send to pane with socket chosen by `!insideTmux` → track agentId→{paneId, insideTmux} → register one cleanup killing ALL tracked panes on leader exit → write initial prompt to the teammate's MAILBOX ("Send initial instructions to teammate via mailbox" — prompts travel by file even for pane teammates). terminate = shutdown_request JSON to mailbox; kill = killPane using the STORED insideTmux flag.
**Invariant:** per-teammate stored routing (`insideTmux`) beats re-detecting at kill time; initial prompts go through the same mailbox as everything else so in-process and pane teammates have ONE message path; isActive is honestly documented as best-effort (pane liveness NOT probed).
**Probe:** coverage caveat (no direct tests). Deterministic probes: `grep -n 'initial instructions to teammate via mailbox' src/utils/swarm/backends/PaneBackendExecutor.ts` (:177); `grep -n 'assume active if we have a record' src/utils/swarm/backends/PaneBackendExecutor.ts` (:340-341).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "createPaneBackendExecutor spawnedTeammates sendCommandToPane", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt thin adapters that add ONLY identity/routing/cleanup around raw resource backends, keeping one messaging channel across execution modes; adapt command templates; omit color assignment if headless.
