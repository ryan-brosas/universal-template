<!-- capsule-v2 -->
# iTerm2 at-fault pane recovery — when a split fails, when may you prune the tracked session ID and when must you not?

**Source:** locoagent (Claude Code CLI fork, MIT), rev `c01bb3f`; Codebase Memory `locoagent`. **Question:** how do you distinguish "targeted teammate pane was closed by the user" from a systemic it2 failure without corrupting your session-ID state?

## Confirm-before-prune retry loop
**Path/Symbol:** `src/utils/swarm/backends/ITermBackend.ts:createTeammatePaneInSwarmView` (:114-240), prune block (:179-208), killPane staleness cleanup (:320-339), parseSplitOutput (:50-56).
**Signature:** bounded retry: each `continue` shrinks `teammateSessionIds` by 1; empty ⇒ `firstPaneUsed = false` ⇒ next iteration has no target ⇒ throws. "Bounded at O(N+1) iterations."
**Data Shape:** module state `teammateSessionIds: string[]` (creation order) + `firstPaneUsed` latch; layout = leader-left, teammates stacked via last-teammate splits.

### Decisive source
```ts
// If we targeted a teammate session, confirm it's actually dead before
// pruning — 'session list' distinguishes dead-target from systemic
// failure (Python API off, it2 removed, transient socket error).
// Pruning on systemic failure would drain all live IDs → state corrupted.
if (targetedTeammateId) {
  const listResult = await runIt2(['session', 'list'])
  if (listResult.code === 0 && !listResult.stdout.includes(targetedTeammateId)) {
    // Confirmed dead — prune and retry with next-to-last (or leader).
    const idx = teammateSessionIds.indexOf(targetedTeammateId)
    if (idx !== -1) teammateSessionIds.splice(idx, 1)
    if (teammateSessionIds.length === 0) firstPaneUsed = false
    continue
  }
  // Target is alive or we can't tell — don't corrupt state, surface the error.
}
```

**Flow:** first teammate splits `-v -s <leaderSessionId>` (UUID parsed from ITERM_SESSION_ID after the colon; fallback to active-session split loses reliable UUIDs — NOTE comment :46-48); subsequent teammates split from LAST tracked ID for vertical stacking → on split failure with a targeted ID: verify via `session list` absence BEFORE pruning, else throw → success path parses `Created new pane: <uuid>` and pushes to tracking → killPane uses `-f` ("without it, iTerm2 respects the 'Confirm before closing' preference... tmux kill-pane has no such prompt") and cleans tracking REGARDLESS of close result.
**Invariant:** destructive state pruning requires positive confirmation of death — ambiguity surfaces as an error instead; every exit from the create loop re-establishes the invariant that tracked IDs are live panes; cosmetics (color/title) deliberately skipped because EACH it2 call spawns a Python process (~slow).
**Probe:** coverage caveat (no direct tests). Deterministic probes: `grep -n 'state corrupted' src/utils/swarm/backends/ITermBackend.ts` (:183); `grep -n 'Confirm before' src/utils/swarm/backends/ITermBackend.ts` (:325-327).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "parseSplitOutput getLeaderSessionId ITermBackend killPane", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt confirm-then-prune recovery for caches of external resource handles; adapt the liveness probe to your backend's listing command; omit AppleScript/iTerm specifics otherwise.
