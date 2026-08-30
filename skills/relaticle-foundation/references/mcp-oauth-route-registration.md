<!-- capsule-v2 -->
# OAuth route registration — boot-deferred override wins the dispatch slot

**Source:** relaticle AGPL-3.0 `main@6e3bf8df`; direct-read fallback (MCP graph absent this session). **Question:** How do you mount an MCP server plus a custom OAuth consent flow without the framework's own routes shadowing your override?

## routes/ai.php + discovery + dynamic registration
**Path/Symbol:** `routes/ai.php` (whole, 35L): middleware chain (:14), oauth throttle group (:16), booted-deferred approve override (:19-24), domain split (:26-34); discovery/registration tests `tests/Feature/Mcp/OAuthDiscoveryTest.php` (whole, 55L).
**Signature:** `Mcp::web($path, RelaticleServer::class)->middleware(['auth:sanctum,api', 'throttle:mcp', SetApiTeamContext::class, EnsureHostedWorkspaceAccess::class])`; `app()->booted(fn => Route::post('/oauth/authorize', [ApproveAuthorizationController::class, 'approve'])->name('passport.authorizations.approve'))`.
**Data Shape:** MCP endpoint at `/mcp` (or `/` on a dedicated `app.mcp_domain`); OAuth routes under pre-auth `throttle:mcp-oauth` (20/min per IP); discovery docs at `/.well-known/oauth-protected-resource` and `/.well-known/oauth-authorization-server` (PKCE S256 only); dynamic client registration POST `/oauth/register` → 201 with `client_id`.

### Decisive source
```php
// Defer registration until after Passport (which boots later) has registered its routes,
// so our POST /oauth/authorize wins the dispatch slot in the route collection.
app()->booted(static function (): void {
    Route::middleware(['web', 'auth', 'throttle:mcp-oauth'])
        ->post('/oauth/authorize', [ApproveAuthorizationController::class, 'approve'])
        ->name('passport.authorizations.approve');
});
```
Clients are owned by the ULID user (`owner_type`/`owner_id`, `oauthApps()` relation) so per-user connector management works; registration is throttled at the same 20/min (the test loops 20×201 then asserts 429).

**Flow:** OAuth discovery + registration + consent endpoints sit behind the pre-auth IP limiter → the MCP tool endpoint sits behind the full authenticated chain (auth guard → per-user throttle → team-context middleware → workspace-access gate) — the exact chain the token-binding and access capsules assume → the approve override is registered inside `app()->booted()` so it is appended AFTER Passport's routes and wins the dispatch slot for the same path+method.
**Invariant:** A route override against a package that registers routes during boot must itself be registered after that boot — a plain top-of-file registration is silently shadowed; keep the package route NAME (`passport.authorizations.approve`) so framework-generated authorize URLs keep resolving to the override.
**Probe:** `tests/Feature/Mcp/OAuthDiscoveryTest.php` (discovery structure, S256-only PKCE, RFC 7591 201 registration, 20/min throttle), `tests/Feature/Mcp/OAuthTeamPickerTest.php` (consent flow through the override).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "relaticle", query: "routes ai.php Mcp web oauthRoutes booted passport.authorizations.approve", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt boot-deferred route overrides with the package's canonical route name, and split pre-auth OAuth traffic from the authenticated tool endpoint into separate throttle domains. Adapt limiter names and middleware to your stack. Omit the dedicated-domain option if single-host. Direct tests pin discovery, registration, and throttling.
