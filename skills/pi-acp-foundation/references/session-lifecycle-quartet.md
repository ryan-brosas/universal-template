<!-- capsule-v2 -->
# Session lifecycle quartet — how does an ACP adapter expose fork/resume/close/listProviders as unstable methods over a single-subprocess agent?

**Source:** pi-acp-jetbrain MIT `main@1f0524f777c93c51747c26d24f3609c2a4e6731d`; Codebase Memory `pi-acp`. **Question:** How do you branch a stored session into a fresh subprocess without mutating the source file, and keep exactly one live subprocess across all entry paths?

## unstable_forkSession / resumeSession / closeSession / unstable_listProviders
**Path/Symbol:** `src/acp/agent.ts` (`unstable_forkSession` :1128-1240, `resumeSession`, `closeSession`, `unstable_listProviders`) + capability declaration in `initialize` (`sessionCapabilities: { list:{}, delete:{}, fork:{}, resume:{}, close:{} }`, `providers: {}`).
**Signature:** `async unstable_forkSession(params: ForkSessionRequest): Promise<ForkSessionResponse>`; fork response carries `_meta.piAcp.fork = { fromSessionId, entryId, text, cancelled, sessionFile? }`; providers via `piModelsToProviderInfo(models)` (one ProviderInfo per distinct provider id; unknown protocol → `` `_${provider}` `` sentinel protocol string).
**Data Shape:** fork = spawn dedicated pi subprocess bound to the SOURCE session file (`--session <path>`), `getEntries` → reverse-find first `{type:'message', message:{role:'user'}}` → `proc.fork(entryId)` (pi branches into a NEW session file + id, source untouched) → re-read `getState` for the new sessionId/sessionFile.

### Decisive source
```ts
// Three-way cleanup: registered sessions dispose their own bridge via the manager;
// unregistered forks own their subprocess+bridge directly. Both post-registration
// awaits (bridge readiness, config) can throw AFTER sessionId is assigned.
} catch (e) {
  if (sessionId) {
    await this.closeManagedSession(sessionId).catch(() => undefined)
  } else {
    proc.dispose()
    await bridge.dispose().catch(() => undefined)
  }
  throw e
}
```

**Flow:** fork validates absolute cwd + known sessionId (from SessionStore) BEFORE spawning; starts its OWN bridge for the new session; on pi-cancelled fork or missing user entries disposes subprocess+bridge and throws `RequestError.internalError` with distinct messages ('source session has no user messages to fork from…' vs 'pi cancelled the fork: <text>'). Success path: register session → wait bridge ready → upsert store with the NEW sessionFile → `closeManagedSessionsExcept(sessionId)` enforces single-live-subprocess → return modes/configOptions from the fresh proc. resumeSession restores from store then likewise closes everything else. closeSession treats close like cancel (best-effort `session.cancel()` swallowed) then releases the subprocess while the session FILE survives for later resume.
**Invariant:** the source session file is never written by a fork; every exit path disposes either the managed session OR (proc + bridge) — never leaks both nor double-disposes; single-live-subprocess policy is applied on fork/resume success but NOT before validation failures.
**Probe:** `npx tsx --test test/unit/session-restore.test.ts test/unit/session-delete.test.ts` (restore/close/store interplay at HEAD).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-acp", query: "unstable_forkSession resumeSession closeManagedSessionsExcept", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the spawn-branch-rebind fork pattern (fork in a dedicated subprocess against the stored file — never mutate the source), the three-way cleanup matrix, and close-keeps-file semantics. Adapt method names/UNSTABLE prefixes to your client's capability negotiation. Omit provider listing unless your backend exposes a models RPC. Direct tests cover restore/delete paths; fork itself is exercised indirectly (needs live pi) — noted caveat.
