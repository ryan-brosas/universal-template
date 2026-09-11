<!-- capsule-v2 -->
# Token-bound team context — how does an OAuth-chosen team ride on the access token, survive refresh grants, and become the authoritative tenant scope for API calls?

**Source:** relaticle AGPL-3.0 `main@6e3bf8dfb7c5`; direct source+test read (Codebase Memory MCP not connected this session). **Question:** When a multi-tenant API is reached via OAuth (MCP clients) or personal access tokens, how does the team chosen at consent time stay bound to every token minted from it — and how does the middleware make that binding authoritative without corrupting web-session state?

## Consent→code→token→middleware binding chain
**Path/Symbol:** `app/Listeners/Mcp/CopyTeamIdToAccessToken.php` (whole, 72L, on Passport's `AccessTokenCreated`; explicitly registered `AppServiceProvider.php:146`); `app/Http/Middleware/SetApiTeamContext.php` (whole, 156L: `handle`, `terminate`, `resolveTeam`, `applyTenantScopes`).
**Signature:** listener: `consentedTeamId(userId, clientId)` = latest `oauth_auth_codes` row for (user, client) with non-null `team_id` → else `inheritedTeamId(userId, clientId, tokenId)` = latest OTHER `oauth_access_tokens` row for (user, client) with non-null `team_id` → else null (silent) → `DB::table('oauth_access_tokens')->where('id', $event->tokenId)->update(['team_id' => $teamId])`.
**Data Shape:** middleware resolution ladder: Passport token → `team_id` REQUIRED (missing/empty = malformed, created outside the consent flow → null → 403); Sanctum PAT → pinned `team_id` → `X-Team-Id` header (must pass `Str::isUlid`) → `currentTeam`; then `belongsToTeam($team)` re-checked even for token-pinned teams.

### Decisive source
```php
// The token is minted in a separate POST /oauth/token request with
// no session, and the `code` parameter there is league's encrypted payload
// rather than the auth code's id, so the token has to be matched back to its
// consent by user and client instead.
```
```php
// Set team in memory only — do NOT call switchTeam() which persists
// current_team_id to the database, corrupting the web panel's team state
// when API calls target a different team than the active web session.
$user->forceFill(['current_team_id' => $team->getKey()]);
$user->setRelation('currentTeam', $team);
```

**Flow:** consent POST stamps `team_id` on the auth code → token endpoint mints the access token (sessionless; the `code` param is league's encrypted payload, not the row id) → `AccessTokenCreated` listener matches consent by (user_id, client_id) and copies `team_id` onto the token → refresh grants (no auth code; `passport:purge` may have removed the original) inherit from the token being replaced → per-request, `SetApiTeamContext` makes the token binding authoritative (headers ignored for Passport), sets context in MEMORY ONLY, overrides to the web guard (`auth()->guard('web')->setUser($user)` + `shouldUse('web')`) so Filament policies/observers/`TeamScope` recognize API callers, and `applyTenantScopes` adds global scopes to the six business models. `terminate()` forgets the guard user, clears tenant context, and `clearBootedModels()` on all six — with an explicit docblock WARNING that the static-scope approach is FPM-only, not Octane-safe (scopes leak across requests if terminate fails). Fail-closed caller-type check: a non-User tokenable → 403 JSON, not an uncaught TypeError (defense-in-depth behind the sanctum provider check).
**Invariant:** The consented team is the ONLY team source for Passport tokens — a header or session must never override it, and a token without one is malformed and rejected. Web-session team state must never be persisted from an API request. Every resolution failure is a clean 401/403, never a 200 with wrong-tenant data.
**Probe:** `tests/Feature/Mcp/OAuthTeamPickerTest.php` (457L) — consent renders teams + capability disclosure, missing/foreign `team_id` rejected, billing-paused workspace unselectable AND 402 on tampered submit, auth-code stamping, header-ignored token-authoritative scoping, no-`team_id` Passport token rejected, PAT honored, cross-provider tokenable 401 (guard) + 403 (middleware), full PKCE dance binds the consented team, refresh keeps it, refresh keeps it after auth-code purge.

## Get live surrounding code
**Retrieve:** (canonical graph form; executed this session as exact-symbol grep fallback — hit confirmed)
```ts
await mcp.codebase_memory.search_graph({ project: "relaticle", query: "CopyTeamIdToAccessToken AccessTokenCreated SetApiTeamContext resolveTeam PassportAccessToken team_id clearBootedModels applyTenantScopes", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the binding chain: consent-time choice stamped on the auth code, copied to the token by an event listener that matches consent by (user, client) with a previous-token inheritance fallback for refresh grants, and a middleware that treats the token binding as authoritative while setting tenant context in memory only. Adopt the memory-only context switch, the web-guard override for policy reuse, and the terminate()-time scope cleanup with an explicit long-running-process safety warning. Adapt Passport/Sanctum specifics to your auth stack. Companion to `mcp-token-ability-gating.md` (the ability plane this team context rides beneath).
