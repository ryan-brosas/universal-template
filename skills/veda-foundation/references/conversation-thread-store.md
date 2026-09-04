<!-- capsule-v2 -->
# Conversation thread store — how do you persist a backend thread id per session so resume survives format migration without corrupting thread identity?

**Source:** Veda (`veda-ts`, MIT, `master@c3c69f2c340ec81ada8ea974076ce5bbaf5ccbc6`); Codebase Memory `veda`. **Question:** A CLI wraps stateful backends (codex threads, claude sessions). Where does the mapping session→backend-thread live, how is it kept concurrency-safe, and what happens to pre-migration data?

## One JSON file per session under the shared advisory lock
**Path/Symbol:** `src/conversation/store.ts:ConversationStore` (whole, 140L): `save` (:34-51), `load` (:55-100, `skipLock` param), `getThreadId` (:105-107), `getBackend` (:113-115), `clear` (:124-132), `exists` (:137-139); shape in `src/conversation/types.ts:ThreadInfo` (whole, 10L); path + validation in `src/util/paths.ts` (`getSessionDir` :51-59, `getThreadPath` :65-67, `getLegacyThreadPath` :75-77, `isValidSessionId` :129-132).
**Signature:** `new ConversationStore({ sessionId: string; baseDir?: string })`; `save(info: Omit<ThreadInfo, 'createdAt' | 'lastUsedAt'>) → Promise<void>`; `load(skipLock = false) → Promise<ThreadInfo | null>`.
**Data Shape:** `ThreadInfo { backend: string; threadId: string; createdAt: string; lastUsedAt: string }` stored as pretty JSON at `<sessionDir>/thread.json`; legacy twin is a bare text file `codex_thread_id` holding just the thread id.

### Decisive source
```ts
async save(info: Omit<ThreadInfo, 'createdAt' | 'lastUsedAt'>): Promise<void> {
    await withLock(this.threadPath, async () => {
      await mkdir(this.sessionDir, { recursive: true });
      // Check if existing thread
      const existing = await this.load(true); // pass "locked" to skip re-acquiring lock
      const threadInfo: ThreadInfo = {
        ...info,
        createdAt: existing?.createdAt ?? new Date().toISOString(),
        lastUsedAt: new Date().toISOString(),
      };
      await Bun.write(this.threadPath, JSON.stringify(threadInfo, null, 2));
    });
  }
```
Legacy migration inside `load`:
```ts
      // Try legacy format
      const threadId = (await legacyFile.text()).trim();
      if (threadId) {
        // Migrate to new format
        const info: ThreadInfo = {
          backend: 'codex', // Legacy was always codex
          threadId,
          createdAt: new Date().toISOString(),
          lastUsedAt: new Date().toISOString(),
        };
        // Save in new format (directly, not via save() to avoid recursion)
        await Bun.write(this.threadPath, JSON.stringify(info, null, 2));
        return info;
      }
```
**Flow:** constructor validates the session id (`isValidSessionId`: 1–64 chars of `[A-Za-z0-9._:-]` — a path-traversal guard BEFORE any path is derived) and derives thread.json + legacy paths → `save` takes the advisory lock, re-reads existing state via `load(true)` (skipLock — withLock is non-reentrant, so the inner read MUST NOT re-acquire), preserves `createdAt` but refreshes `lastUsedAt`, writes → `load` tries thread.json first (parse errors ignored → fall through), then the legacy file, transparently upgrading it on first read → `clear` deletes under the lock, ignoring absence.
**Invariant:** `createdAt` is thread identity (preserved across every save); `lastUsedAt` is recency (always refreshed). The inner `load(true)` must skip the lock — a re-acquiring read inside `withLock` deadlocks against the non-reentrant lock primitive. Session-dir resolution prefers explicit `baseDir` > `VEDA_HOME` env > project-local `.veda/sessions` (when a git root exists) > user-global `~/.config/veda`, so sessions travel with the repo by default.
**Probe:** `tests/conversation/store.test.ts` (executed live at pin: 10 pass / 0 fail) pins invalid-session-id throw, save/load round-trip, `createdAt` preservation across update, legacy migration (backend hardcoded 'codex'), per-session isolation, and clear/exists.
**Coverage caveat:** no test pins the skipLock re-entrancy contract directly — it is source-pinned (withLock non-reentrancy from the stale-lock-takeover capsule).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "veda", query: "ConversationStore thread.json save load skipLock legacy codex_thread_id migration", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the one-JSON-file-per-session store: validate session ids before path derivation, lock-guarded read-modify-write with a skipLock inner read, createdAt-identity vs lastUsedAt-recency split, and transparent legacy migration that hardcodes the old system's only possible value. Adapt the session-dir precedence ladder to your host's project-local convention. Omit legacy migration once your format has no legacy users.
