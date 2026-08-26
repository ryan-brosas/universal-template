<!-- capsule-v2 -->
# Environment detection capture-at-import — which tmux are you actually inside?

**Source:** locoagent (Claude Code CLI fork, MIT), rev `c01bb3f`; Codebase Memory `locoagent`. **Question:** how do you detect "running inside tmux" without false positives from OTHER tmux servers on the machine, and why must the env var be captured at import time?

## ORIGINAL_USER_TMUX module-load snapshot
**Path/Symbol:** `src/utils/swarm/backends/detection.ts:ORIGINAL_USER_TMUX` (:9-10), `ORIGINAL_TMUX_PANE` (:17-19), `isInsideTmuxSync` (:36-38), `getLeaderPaneId` (:66-68), `isInITerm2` (:90-104), `isIt2CliAvailable` (:117-120).
**Signature:** `isInsideTmuxSync(): boolean`; `isInsideTmux(): Promise<boolean>` (cached); `getLeaderPaneId(): string | null`.
**Data Shape:** `const ORIGINAL_USER_TMUX = process.env.TMUX` captured at MODULE LOAD; per-result boolean caches (`isInsideTmuxCached`, `isInITerm2Cached`).

### Decisive source
```ts
/**
 * Captured at module load time to detect if the user started Claude from within tmux.
 * Shell.ts may override TMUX env var later, so we capture the original value.
 */
const ORIGINAL_USER_TMUX = process.env.TMUX
// ...
// IMPORTANT: We ONLY check the TMUX env var. We do NOT run `tmux display-message`
// as a fallback because that command will succeed if ANY tmux server is running
// on the system, not just if THIS process is inside tmux.
export function isInsideTmuxSync(): boolean {
  return !!ORIGINAL_USER_TMUX
}
```

**Flow:** import-time capture → boolean caches memoize forever (environment can't change mid-process) → `isTmuxAvailable()` separately probes `tmux -V` exit code (installed ≠ inside) → iTerm2 detection ORs three indicators: `TERM_PROGRAM === 'iTerm.app'` || `ITERM_SESSION_ID` present || `env.terminal` heuristic → it2 availability deliberately probes `it2 session list` NOT `--version`, because `--version` succeeds even when the Python API is disabled and would cause `session split` to fail later with no fallback.
**Invariant:** "inside tmux" means THE USER STARTED THIS PROCESS INSIDE TMUX — never inferred by querying servers; leader pane identity (`TMUX_PANE`) is frozen at startup so pane targeting stays correct even after the user switches panes; probe with the operation you'll actually need, not a cheaper command that lies.
**Probe:** coverage caveat (no direct tests). Deterministic probes: `grep -n 'ANY tmux server' src/utils/swarm/backends/detection.ts` (:33-34); `grep -n "session', 'list'" src/utils/swarm/backends/detection.ts` (:118).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "isInsideTmux isIt2CliAvailable isInITerm2 getLeaderPaneId", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt import-time env snapshots for any identity that later operations mutate (shell wrappers WILL clobber `TMUX`), env-only containment checks with explicit comments forbidding server-query fallbacks, and capability probes that exercise the real API path; adapt indicator lists per terminal; omit the macOS-specific iTerm heuristics if not porting to mac.
