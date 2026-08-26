<!-- capsule-v2 -->
# session identity atomic switch — how do you change a session ID and its storage directory without ever letting them disagree?

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** How do you swap an active session identity (ID + where its transcript lives + lineage) atomically, and clean up derived caches on every transition?

## switchSession / regenerateSessionId: pair-or-nothing transitions + bounded caches
**Path/Symbol:** `src/bootstrap/state.ts`:`regenerateSessionId` (`:435-450`), `switchSession` (`:468-479`), `onSessionSwitch` signal (`:481-489`), `getSessionProjectDir` (`:496-498`).
**Signature:** `regenerateSessionId(options?: { setCurrentAsParent?: boolean }): SessionId`; `switchSession(sessionId: SessionId, projectDir: string | null = null): void`; `onSessionSwitch: (cb: (id: SessionId) => void) => unsubscribe` (re-exported `.subscribe`).
**Data Shape:** Pair `{ sessionId: SessionId, sessionProjectDir: string | null }` — `null` means "derive transcript dir from originalCwd at read time"; non-null is `dirname(transcriptPath)` for cross-project/worktree resumes. Lineage: `parentSessionId` (e.g. plan-mode → implementation chains). Side cache: `planSlugCache: Map<sessionId, wordSlug>`.

### Decisive source
```ts
export function regenerateSessionId(options = {}) {
  if (options.setCurrentAsParent) {
    STATE.parentSessionId = STATE.sessionId          // lineage bookend BEFORE minting
  }
  STATE.planSlugCache.delete(STATE.sessionId)        // drop outgoing slug entry
  STATE.sessionId = randomUUID() as SessionId
  STATE.sessionProjectDir = null                     // regenerated sessions live HERE
  return STATE.sessionId
}

export function switchSession(sessionId, projectDir = null) {
  STATE.planSlugCache.delete(STATE.sessionId)
  STATE.sessionId = sessionId
  STATE.sessionProjectDir = projectDir
  sessionSwitched.emit(sessionId)
}
```

**Flow:** `/clear`-style regeneration → optional parent capture → slug-cache eviction for outgoing ID → new UUID + projectDir reset to null → resume/cross-project load → `switchSession(newId, dirname(jsonl))` → both fields written together → `sessionSwitched` signal fires → external listeners (e.g. concurrentSessions PID-file tracker) re-sync themselves via `onSessionSwitch` because bootstrap cannot import them (DAG leaf).
**Invariant:** There is NO separate setter for `sessionId` or `sessionProjectDir` anywhere in the file — the doc comment states they "always change together … cannot drift out of sync (CC-34)". Every transition deletes the OUTGOING session's plan-slug entry first, keeping `planSlugCache` bounded across repeated `/resume`; callers that need the slug across the switch (REPL clearContext) read it BEFORE calling. `projectDir` never carries over from the previous session — every call resets it, defaulting to null (current-project derivation). Regeneration also resets project dir so regenerated transcripts land in the current project, not the resumed-from one.
**Probe:** Deterministic pins (no upstream runner): `search_graph --project locoagent --name-pattern "switchSession|regenerateSessionId"` resolves `src/bootstrap/state.ts` `468-479` and `435-450` line-exact; `grep -n 'cannot drift out of sync' src/bootstrap/state.ts` → `459:`; `grep -n 'planSlugCache.delete(STATE.sessionId)' src/bootstrap/state.ts` → `444:` AND `475:` (two sites).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "switchSession sessionProjectDir planSlugCache", limit: 10 });
```

## Verdict
Adopt atomic-pair session switching (single function owns both writes, no individual setters) plus eviction-on-transition for per-ID side caches and an explicit post-switch signal for out-of-band listeners. Adapt lineage capture (`setCurrentAsParent`) to your mode stack. Omit the CC-34 issue-reference convention.
