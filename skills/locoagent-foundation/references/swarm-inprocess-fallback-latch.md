<!-- capsule-v2 -->
# In-process fallback latch — when spawn degrades to in-process, how does the UI find out and why is the latch scoped to auto mode?

**Source:** locoagent (Claude Code CLI fork, MIT), rev `c01bb3f`; Codebase Memory `locoagent`. **Question:** after one teammate falls back from panes to in-process execution, what must every later spawn and every UI banner see?

## markInProcessFallback + isInProcessEnabled gate
**Path/Symbol:** `src/utils/swarm/backends/registry.ts:markInProcessFallback` (:326-329), `isInProcessEnabled` (:351-389), `getResolvedTeammateMode` (:396-398).
**Signature:** `markInProcessFallback(): void`; `isInProcessEnabled(): boolean`.
**Data Shape:** module boolean `inProcessFallbackActive` — write-once latch (never cleared except by test-only `resetBackendDetection`).

### Decisive source
```ts
} else {
  // 'auto' mode - if a prior spawn fell back to in-process because no pane
  // backend was available, stay in-process (scoped to auto mode only so a
  // mid-session Settings change to explicit 'tmux' still takes effect).
  if (inProcessFallbackActive) {
    return true
  }
  const insideTmux = isInsideTmuxSync()
  const inITerm2 = isInITerm2()
  enabled = !insideTmux && !inITerm2
}
```
Preceding hard overrides: non-interactive (`-p`) sessions ALWAYS force in-process ("tmux-based teammates don't make sense without a terminal UI"); mode `'in-process'` ⇒ true; `'tmux'` ⇒ false.

**Flow:** spawn tries pane backend → none available → caller sets `markInProcessFallback()` → every subsequent `isInProcessEnabled()` returns true so banner/teams menu/spawn short-circuit reflect reality ("the environment won't change mid-session") → BUT an explicit user switch to 'tmux' mode in Settings still takes effect because the latch is checked only inside the 'auto' branch.
**Invariant:** fallback state must be observable by BOTH the executor chooser and the presentation layer through ONE predicate; the latch never fights an explicit user decision.
**Probe:** coverage caveat (no direct tests). Deterministic probe: `grep -n 'scoped to auto mode only' src/utils/swarm/backends/registry.ts` (:370-371).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "markInProcessFallback isInProcessEnabled getResolvedTeammateMode", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt write-once degradation latches scoped to automatic modes so explicit configuration always wins; adapt predicate names; omit nothing — this shape ports as-is.
