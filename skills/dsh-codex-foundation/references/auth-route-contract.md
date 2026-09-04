<!-- capsule-v2 -->
# Auth route contract — authorize before side effects, exact methods, effect-owned teardown

**Source:** dsh-codex Apache-2.0 `main@e3e54e206f7c829503c7e6eed378643ba0416792`; Codebase Memory `dsh-codex`. **Question:** how should a plugin compose exact auth endpoints so origin authorization precedes provider/store work, methods and errors are stable JSON, and route registration disposes its auth owner?

## registerOpenAICodexAuthRoutes and auth-path constants
**Path/Symbol:** `src/auth-paths.ts:3-8 OPENAI_CODEX_AUTH_*_PATH`, `src/auth-routes.ts:346-353 json`, `src/auth-routes.ts:487-619 registerOpenAICodexAuthRoutes`.
**Signature:** `registerOpenAICodexAuthRoutes(ctx: Context, store: OpenAICodexCredentialStore, trustedOriginsOverride?, fastModeOverride?, imageTools?): void`. It registers exact `GET /plugins/dsh-openai-codex/auth/status`, `POST /plugins/dsh-openai-codex/auth/login`, and `POST /plugins/dsh-openai-codex/auth/logout` routes (plus optional settings routes).
**Data Shape:** Every response is JSON with `content-type: application/json; charset=utf-8`, `cache-control: no-store`, and `x-content-type-options: nosniff`. Status returns `auth.status()`; login returns `auth.signIn()` or a safe 500; logout returns `{ ok: true }` or a safe 500; rejected trust is `403 { error }` and wrong methods are `405 { error: 'method not allowed' }`.

### Decisive source
```ts
const authorize = async (req, res): Promise<boolean> => {
  const decision = await trustedRequestDecision(req, trustedOrigins)
  if (decision.trusted) return true
  json(res, 403, { error: decision.error })
  return false
}

ctx.webServer.register({
  kind: 'exact', path: OPENAI_CODEX_AUTH_STATUS_PATH,
  handler: async (req, res) => {
    if (req.method !== 'GET') return json(res, 405, { error: 'method not allowed' })
    if (!await authorize(req, res)) return
    json(res, 200, await auth.status())
  },
})

return async () => {
  for (const dispose of routes) dispose()
  await auth.dispose()
}
```

**Flow:** construct one `OpenAICodexWebAuth` and selected sidecar/registries → install exact routes inside `ctx.effect` → each handler checks method, then calls the shared origin authorizer, then invokes auth/settings work → errors are converted to safe JSON → effect cleanup unregisters every route and disposes the auth owner.
**Invariant:** unauthorized requests cannot call `auth.status`, `auth.signIn`, or `auth.signOut`; route paths are exact and method contracts are explicit; JSON responses are non-cacheable and MIME-sniff resistant; teardown unregisters all handles and drains active sign-in.
**Probe:** `tests/auth-routes.spec.ts:74-92` (captured exact route registration), `tests/auth-routes.spec.ts:204-226` (remote authorization blocks all three auth routes before mocks), and `tests/auth-routes.spec.ts:142-172` (optional settings route uses GET/POST and JSON projection). The source registration range 487-619 was read in full; direct test range 40 is only the parse-partial import line.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: 'dsh-codex', qn_pattern: 'dsh-codex\\.src\\.auth-routes\\.registerOpenAICodexAuthRoutes', limit: 10, fields: ['signature', 'name', 'file'] });
```

## Verdict
Adopt the authorize-before-side-effect route composition, exact path/method registration, no-store JSON envelope, and context-owned cleanup. Adapt the web framework registration/effect API and provider route constants; keep optional settings routes behind explicit dependency injection. Omit catch-all routes or handlers that parse/mutate credentials before trust and method checks. Coverage: `src/auth-routes.ts`, `src/auth-paths.ts`, and `tests/auth-routes.spec.ts` have `metadata_match`; the test file remains `partial` at line 40, but cited behavior ranges were directly read.
