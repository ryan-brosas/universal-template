<!-- capsule-v2 -->
# Backend detection ladder — in which order do tmux / iTerm2 / it2 claims get checked, and what does each failure mean?

**Source:** locoagent (Claude Code CLI fork, MIT), rev `c01bb3f`; Codebase Memory `locoagent`. **Question:** when several terminal multiplexers are present, which backend wins and how is "iTerm2 without it2" distinguished from "no pane backend at all"?

## Priority ladder with cached result + user-preference veto
**Path/Symbol:** `src/utils/swarm/backends/registry.ts:detectAndGetBackend` (:136-254), `getTmuxInstallInstructions` (:259-285), `getBackendByType` (:295-302).
**Signature:** `detectAndGetBackend(): Promise<BackendDetectionResult>` where result = `{ backend: PaneBackend; isNative: boolean; needsIt2Setup?: boolean }`.
**Data Shape:** module caches `cachedBackend` + `cachedDetectionResult` — selection is FIXED for process lifetime after first detection.

### Decisive source
```ts
// In iTerm2 but it2 not available - check if tmux can be used as fallback
const tmuxAvailable = await isTmuxAvailable()
if (tmuxAvailable) {
  // Return tmux as fallback. Only signal it2 setup if the user hasn't already
  // chosen to prefer tmux - otherwise they'd be re-prompted on every spawn.
  const backend = createTmuxBackend()
  cachedBackend = backend
  cachedDetectionResult = { backend, isNative: false, needsIt2Setup: !preferTmux }
  return cachedDetectionResult
}
```

**Flow:** inside-tmux ⇒ tmux native (`isNative: true`) ALWAYS wins even under iTerm2 → in-iTerm2: user's `preferTmuxOverIterm2` config vetoes native panes; else it2 available ⇒ iTerm2 native; else tmux-fallback with `needsIt2Setup: !preferTmux` (polarity: the flag means "would prompt", suppressed exactly when the user already chose tmux) → plain terminal with tmux installed ⇒ external-session tmux (`isNative: false`) → nothing ⇒ throw platform-specific install instructions (brew/apt/dnf/WSL text per `getPlatform()`).
**Invariant:** detection runs ONCE; `needsIt2Setup` must be false whenever the user has expressed a preference, or the setup prompt reappears on every spawn; `isNative` separately answers "will teammates be visible as panes next to the leader".
**Probe:** coverage caveat (no direct tests). Deterministic probe: `grep -n 'needsIt2Setup: !preferTmux' src/utils/swarm/backends/registry.ts` (:219); ladder comment block :129-134.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "detectAndGetBackend BackendDetectionResult getTmuxInstallInstructions", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt the ordered environment-claim ladder with a sticky once-per-process verdict and tri-state results that separate "native", "degraded fallback", and "setup needed"; adapt the specific backends; omit the ant-only telemetry strings.
