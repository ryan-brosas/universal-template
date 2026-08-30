<!-- capsule-v2 -->
# newSession choreography — in what order must a session-create probe state/models, clean up failures, and defer notifications so a half-started session never leaks?

**Source:** pi-acp-jetbrain MIT `main@1f0524f777c93c51747c26d24f3609c2a4e6731d`; Codebase Memory `pi-acp`. **Question:** What is the exact ordered choreography of newSession — parallel probes, the four-branch cleanup ladder, and the setTimeout(0) deferrals?

## PiAcpAgent.newSession — ordered choreography
**Path/Symbol:** `src/acp/agent.ts:newSession` (:392-563) — parallel probes :425-441, cleanup ladder :443-483, prelude :485-511, single-live sweep :517, response :519-531, deferrals :533-562.
**Signature:** `async newSession(params: NewSessionRequest)` — response `{sessionId, configOptions, models, modes, _meta: {piAcp: {startupInfo}}}`.
**Data Shape:** probes are ok/error envelopes: `Promise.all([getState→{ok,value}|{ok:false,error}], [getAvailableModels→…]])` — one slow/failing RPC never serializes or kills startup; `rawModelsCount = Array.isArray(models) ? models.length : 0`.

### Decisive source
```ts
const [stateResult, modelsResult] = await Promise.all([
  session.proc.getState().then(s => ({ ok: true as const, value: s })).catch(err => ({ ok: false as const, error: err })),
  session.proc.getAvailableModels().then(m => ({ ok: true as const, value: m })).catch(err => ({ ok: false as const, error: err }))
])
const availableModelsAuthErr = maybeAuthRequiredError(availableModelsErr)
if (availableModelsAuthErr) { await this.cleanupFailedNewSession(session.sessionId, state); throw availableModelsAuthErr }
if (availableModelsErr) { await this.cleanupFailedNewSession(session.sessionId, state); throw RequestError.internalError({}, …) }
if (rawModelsCount === 0) { await this.cleanupFailedNewSession(session.sessionId, state); throw RequestError.authRequired({ authMethods: getAuthMethods() }, 'Configure an API key or log in with an OAuth provider.') }
if (stateErr && maybeAuthRequiredError(stateErr)) { await this.cleanupFailedNewSession(session.sessionId, state); throw RequestError.authRequired({ authMethods: getAuthMethods() }, …) }
```

**Flow:** absolute-cwd guard → `lastSessionCwd` update → `loadSlashCommands` + `getEnableSkillCommands` → `startBridge` (degradation ladder; bridge disposed if `sessions.create` rejects) → `waitForBridgeReady` → PARALLEL state+models probes → cleanup ladder in pinned order: models-auth-error → cleanup + authRequired; models non-auth error → cleanup + internalError; EMPTY model list → cleanup + authRequired (unauthenticated); state auth-error → cleanup + authRequired → `getSessionConfiguration` → startup-info prelude (quiet mode keeps only the update notice) → `closeManagedSessionsExcept` (one live subprocess per connection) → response. TWO `setTimeout(0)` deferrals AFTER the response: pending startup-info delivery, then `available_commands_update` (pi getCommands path with legacy file-command fallback, merged with builtins).
**Invariant:** EVERY failure after `sessions.create` runs `cleanupFailedNewSession` (close managed session + unlink the orphan session file from state-or-store + `store.delete`) BEFORE throwing — a half-started session never leaks a subprocess, a file, or a store row; the empty-model-list case is treated as UNAUTHENTICATED, not an error; notifications defer one macrotask past the response so the client already knows the sessionId (Zed drops unknown-sessionId notifications).
**Probe:** `node --import tsx --test test/unit/new-session-runtime-startup-errors.test.ts test/unit/new-session-auth-required-when-no-models.test.ts test/unit/new-session-pi-not-found.test.ts` (cleanup ladder, empty-models authRequired, spawn failure) — executed GREEN at pin (pass 4).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-acp", query: "newSession cleanupFailedNewSession maybeAuthRequiredError available_commands_update setTimeout", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the parallel ok/error probe envelopes, the ordered cleanup-before-throw ladder, empty-models-means-unauthenticated, and response-then-deferred-notifications. Adapt the probe RPC names and auth error shape to your backend. Omit the quiet-startup prelude suppression unless your client renders startup text. Coverage caveat: the deferral ORDER (startup-info before commands) is source-read; the ladder branches are test-pinned.
