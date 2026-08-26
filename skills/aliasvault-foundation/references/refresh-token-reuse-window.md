<!-- capsule-v2 -->
# Refresh-token rotation reuse window — how do concurrent client refreshes avoid a death spiral?

**Source:** aliasvault AGPL-3.0 (patterns-only) `main@95903e926f757046ef32feb7ca147900de0a6802`; Codebase Memory `ext-aliasvault`. **Question:** When two tabs refresh the same token simultaneously, why doesn't one of them get logged out?

## 30-second PreviousTokenValue grace
**Path/Symbol:** `apps/server/AliasVault.Api/Controllers/AuthController.cs:1129-1178` (`GenerateNewTokensForUser(user, existingTokenValue)`), :1101-1120 (extendedLifetime overload), static `Semaphore` :78.
**Signature:** `Task<TokenModel?> GenerateNewTokensForUser(AliasVaultUser user, string existingTokenValue)`; new row stores `PreviousTokenValue = old`.
**Data Shape:** Refresh tokens are opaque 32-byte base64 strings persisted in `AliasVaultUserRefreshTokens` with `DeviceIdentifier`, `IpAddress` (anonymized), `ExpireDate`, `CreatedAt`, and the rotation link `PreviousTokenValue`.

### Decisive source
```csharp
// Token reuse window:
// Check if a new refresh token was already generated for the current token in the last 30 seconds.
// If yes, then return the already generated new token. This is to prevent client-side race conditions.
var existingTokenReuseWindow = timeProvider.UtcNow.AddSeconds(-30);
var existingTokenReuse = await context.AliasVaultUserRefreshTokens
    .FirstOrDefaultAsync(t => t.UserId == user.Id &&
                                t.PreviousTokenValue == existingTokenValue &&
                                t.CreatedAt > existingTokenReuseWindow);
if (existingTokenReuse is not null)
{
    var accessToken = GenerateJwtToken(user);
    return new TokenModel { Token = accessToken, RefreshToken = existingTokenReuse.Value };
}
```

**Flow:** refresh request → semaphore serializes per-process → reuse-window lookup by (userId, previous==old, created>now-30s): HIT returns the SAME successor token to both racers; MISS → load old row, reject if expired, remove it, mint successor carrying `PreviousTokenValue=old` and the OLD row's remaining lifetime (`existingTokenLifetime = ExpireDate - CreatedAt`, :1163).
**Invariants:** (1) Rotation preserves lifetime — a remember-me token rotates into another long-lived token, not a short one. (2) The reuse window makes refresh idempotent for 30s but NOT forever: replaying an OLD-old token fails because its successor's PreviousTokenValue no longer matches. (3) All mutation paths hold the static `Semaphore(1,1)`; `finally` releases it (2 release sites). (4) Access JWTs are stateless 600-second tokens (`AccessTokenValiditySeconds` :73); only refresh tokens hit the DB.
**Probe:** `grep -c 'AddSeconds(-30)' apps/server/AliasVault.Api/Controllers/AuthController.cs` → `1`; `grep -c 'PreviousTokenValue == existingTokenValue' apps/server/AliasVault.Api/Controllers/AuthController.cs` → `1`; `grep -c 'Semaphore.Release()' apps/server/AliasVault.Api/Controllers/AuthController.cs` → `2`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-aliasvault", query: "GenerateNewTokensForUser", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt successor-linked rotation rows + bounded reuse window as the anti-race pattern; adapt persistence/locking to your stack; omit ASP.NET Identity specifics. Source confirmed at pin `95903e92`; behavior covered indirectly by E2E auth suites, not unit tests (coverage caveat).
