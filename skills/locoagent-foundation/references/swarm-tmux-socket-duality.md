<!-- capsule-v2 -->
# Tmux socket duality — user session vs external swarm session: which commands go to which tmux server?

**Source:** locoagent (Claude Code CLI fork, MIT), rev `c01bb3f`; Codebase Memory `locoagent`. **Question:** when the leader runs OUTSIDE tmux, how do teammates get panes without touching the user's existing tmux sessions?

## runTmuxInUserSession vs runTmuxInSwarm + PID-suffixed socket
**Path/Symbol:** `src/utils/swarm/backends/TmuxBackend.ts:runTmuxInUserSession` (:77-81), `runTmuxInSwarm` (:87-91); `src/utils/swarm/constants.ts:getSwarmSocketName` (:12-14), `SWARM_SESSION_NAME`/`HIDDEN_SESSION_NAME` (:2-5).
**Signature:** `getSwarmSocketName(): \`claude-swarm-${process.pid}\``.
**Data Shape:** every PaneBackend op takes `useExternalSession?: boolean`; the flag selects the runner, never the caller's guess.

### Decisive source
```ts
// constants.ts:
/**
 * Gets the socket name for external swarm sessions (when user is not in tmux).
 * Uses a separate socket to isolate swarm operations from user's tmux sessions.
 * Includes PID to ensure multiple Claude instances don't conflict.
 */
export function getSwarmSocketName(): string {
  return `claude-swarm-${process.pid}`
}
// hidePane moves a pane into a DETACHED session instead of killing it:
await runTmux(['new-session', '-d', '-s', HIDDEN_SESSION_NAME])
const result = await runTmux(['break-pane', '-d', '-s', paneId, '-t', `${HIDDEN_SESSION_NAME}:`])
```

**Flow:** inside-tmux spawns target the USER's server (split leader's window, 30%/70% main-vertical with leader at `resize-pane -x 30%`) → outside spawns create `claude-swarm-<pid>` socket with a `claude-swarm` session + `swarm-view` window (idempotent has-session/list-windows/new-window ladder in createExternalSwarmSession :467-546) and tile-layout rebalance (no leader pane) → first external teammate reuses the window's initial pane (`firstPaneUsedForExternal` latch) → hide/show = break-pane into detached `claude-hidden` session / join-pane back followed by layout reapplication.
**Invariant:** swarm operations on a foreign server must NEVER leak into the user's sessions — isolation by named socket keyed to the process; boolean per-call routing beats inferring the target from context; hidden ≠ killed (pane keeps running).
**Probe:** coverage caveat (no direct tests). Deterministic probes: `grep -n 'claude-swarm-' src/utils/swarm/constants.ts` (:13); `grep -n 'break-pane' src/utils/swarm/backends/TmuxBackend.ts` (:288).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "createExternalSwarmSession runTmuxInSwarm getSwarmSocketName hidePane", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt PID-namespaced auxiliary servers for any tool the host user may also be running personally, with explicit per-operation target flags; adapt session/window names; omit hide/show if your backend lacks an equivalent.
