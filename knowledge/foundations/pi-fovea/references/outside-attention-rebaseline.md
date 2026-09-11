<!-- capsule-v2 -->
# Outside-attention silent re-baseline — how do sibling-workspace changes stay invisible without going stale?

**Source:** pi-fovea MIT `main@5bd4e6f`; Codebase Memory `mnt-hdd-utopia-inspo-pi-fovea`. **Question:** Session-scoped sync ignores files outside the directories the conversation entered — but ignoring drift forever would make every later verdict wrong. Where does the baseline move silently, and what is deliberately preserved?

## Adopt-and-preserve re-baseline with outsideAttention ack
**Path/Symbol:** `src/core/sync.ts:sync` outsideAttentionOnly branch (:423-448); scope predicates (:380-420); session scopes `src/core/session.ts:syncScopeForPath/observeSessionPaths` (:70-84).
**Signature:** `syncScopeForPath(root, path): string|undefined` — top-level child = logical scope (root files are exact scopes); `SyncOutcome.details = {outsideAttention: true, attentionScopes, ignoredFiles, changedFiles: [], ...}`.
**Data Shape:** trigger condition: scoped sync AND ignoredFiles>0 AND changed==deleted==added==removed==0; new baseline spreads the FRESH snapshot then re-attaches `{heat, warmthArmed, pushed}` from the previous baseline.

### Decisive source
```ts
// Coverage enrollment is not authored task drift. Adopt sibling-directory
// changes silently so the broad umbrella graph stays current without
// waking this session or replaying the same change on its next turn.
if (outsideAttentionOnly) {
  warmCache.delete(root);
  setBaseline(root, {
    ...(await snapshot(state)),
    heat: prev.heat,
    warmthArmed: prev.warmthArmed,
    pushed: prev.pushed,
  });
  return { structural: true, red: false, tokens: 0,
    details: { version: state.version, outsideAttention: true, attentionScopes, ignoredFiles, ... } };
}
```

**Flow:** all drift falls outside the session's attention scopes → adopt a fresh snapshot (so the same change never replays) while carrying over the charged heat ledger, hysteresis latch, and embed-once set → report structural=true/red=false with `outsideAttention:true` + the ignored list → next sync sees no delta.
**Invariant:** the silent adoption fires ONLY when NOTHING inside attention moved; any in-scope change takes the normal verdict path; warm cache is invalidated because its key (version+filesKey) no longer matches the adopted baseline; heat memory survives — sibling work must not cool or re-fire THIS session's charged nodes.
**Probe:** `tests/workspace.test.ts` — "indexes nested drift without steering a session focused elsewhere" (:182-220: outcome red=false + `outsideAttention:true`, `ignoredFiles` contains sub/a.ts, state DOES contain it, and the FOLLOW-UP sync returns `structural:false`); `tests/extension.test.ts` — "silently absorbs hintless drift before the session enters a directory".

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pi-fovea", query: "outsideAttention ignoredFiles sync", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt for any per-session relevance filter over shared indexes: absorb out-of-scope drift into the baseline, keep per-session memory intact, acknowledge quietly. Adapt scope granularity (top-level dir here). Omit pi session plumbing.
