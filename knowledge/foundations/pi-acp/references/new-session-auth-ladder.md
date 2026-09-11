<!-- capsule-v2 -->
# New-session post-spawn probe ladder — when is "no models" an auth error, and what must be cleaned up on failure?

**Source:** pi-acp-jetbrain MIT `main@1f0524f777c93c51747c26d24f3609c2a4e6731d`; Codebase Memory `pi-acp`. **Question:** After spawning the agent child, which post-spawn probes decide `authRequired` vs `internalError`, and how do you guarantee a failed session/new leaves no orphan subprocess, session file, or store entry?

## Probe ladder + cleanupFailedNewSession
**Path/Symbol:** `src/acp/agent.ts:PiAcpAgent.newSession` (:430-475), `cleanupFailedNewSession` (:220-238); `src/acp/auth-required.ts:maybeAuthRequiredError` (:9-37).
**Signature:** `newSession(params): Promise<NewSessionResponse>`; `cleanupFailedNewSession(sessionId, state?): Promise<void>`.
**Data Shape:** Probes run as `Promise.all` of `{ok:true,value}|{ok:false,error}` envelopes so one rejection never rejects the batch; state carries `sessionFile` used for cleanup.

### Decisive source
```ts
const [stateResult, modelsResult] = await Promise.all([
  session.proc.getState().then(s => ({ ok: true as const, value: s }))
    .catch(err => ({ ok: false as const, error: err })),
  session.proc.getAvailableModels().then(m => ({ ok: true as const, value: m }))
    .catch(err => ({ ok: false as const, error: err }))
])
...
const availableModelsAuthErr = maybeAuthRequiredError(availableModelsErr)
if (availableModelsAuthErr) { await this.cleanupFailedNewSession(session.sessionId, state); throw availableModelsAuthErr }
if (availableModelsErr) { await this.cleanupFailedNewSession(...); throw RequestError.internalError({}, String(...)) }
// If pi has no models available after spawning, it's effectively unauthenticated.
const rawModelsCount = Array.isArray(availableModels?.models) ? availableModels?.models.length : 0
if (rawModelsCount === 0) {
  await this.cleanupFailedNewSession(session.sessionId, state)
  throw RequestError.authRequired({ authMethods: getAuthMethods() },
    'Configure an API key or log in with an OAuth provider.')
}
if (stateErr && maybeAuthRequiredError(stateErr)) { /* same authRequired path */ }
```
```ts
private async cleanupFailedNewSession(sessionId, state?) {
  await this.closeManagedSession(sessionId)
  const sessionFile = (typeof state?.sessionFile === 'string' && state.sessionFile.trim())
    ? state.sessionFile : this.store.get(sessionId)?.sessionFile
  if (typeof sessionFile === 'string' && sessionFile.trim()) {
    try { if (existsSync(sessionFile)) unlinkSync(sessionFile) } catch { /* primary error wins */ }
  }
  this.store.delete(sessionId)
}
```

**Flow:** spawn → parallel getState + getAvailableModels (each error-captured) → models error that looks auth-shaped → rethrow authRequired; other models errors → internalError with message passthrough → EMPTY model list ⇒ treated as unauthenticated (authRequired carrying fresh authMethods) → state-error auth check → only then config/prelude choreography continues. EVERY failure path calls cleanupFailedNewSession first.
**Invariant:** A failed session/new must leave zero residue: managed session closed, pi JSONL session file unlinked (resolved from live state or the persistent store fallback), store entry deleted — and cleanup failures are swallowed so they never mask the primary error code.
**Probe:** `test/unit/new-session-runtime-startup-errors.test.ts` ("newSession returns AUTH_REQUIRED when pi reports an auth error after spawn" pins `-32000`, `closeCalls:['s-auth']`, `existsSync(sessionFile)===false`, `store.get('s-auth')===null`; "…Internal error on non-auth model probe failures" pins `-32603` with message passthrough) + `test/unit/new-session-auth-required-when-no-models.test.ts` (empty-models variant).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-acp", query: "newSession cleanup failed session auth required models probe", limit: 10 });
// -> pi-acp.src.acp.agent.PiAcpAgent.cleanupFailedNewSession src/acp/agent.ts 220-238
```

## Verdict
Adopt the ok/error envelope probe pattern, the "empty model list == unauthenticated" mapping, and the three-surface cleanup (subprocess, session file, store row). Adapt which probe signals auth in your agent (here it's the model list). Omit nothing else — the ladder is short and every branch is test-pinned at HEAD. Coverage: both cited paths `no_recorded_issue`; suites executed GREEN this pass (2/2 + related).
