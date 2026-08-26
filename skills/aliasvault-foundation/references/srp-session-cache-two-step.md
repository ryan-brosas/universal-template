<!-- capsule-v2 -->
# Two-step SRP session cache — how does a stateless API carry the server ephemeral from initiate to validate?

**Source:** aliasvault AGPL-3.0 (patterns-only) `main@95903e926f757046ef32feb7ca147900de0a6802`; Codebase Memory `ext-aliasvault`. **Question:** Where is the server's SRP secret b stored between the two login POSTs, and how are stale/absent sessions distinguished from wrong passwords?

## Ephemeral cache keyed by srpIdentity
**Path/Symbol:** `apps/server/AliasVault.Api/Controllers/AuthController.cs:174-181` (Login set), `apps/server/AliasVault.Api/Helpers/AuthHelper.cs:39-65` (`ValidateSrpSession` get+derive).
**Signature:** `cache.Set(AuthHelper.CachePrefixEphemeral + srpIdentity, ephemeral.Secret, TimeSpan.FromMinutes(5));` / `(SrpSession? Session, bool ActiveSessionFound) ValidateSrpSession(IMemoryCache cache, AliasVaultUser user, string clientEphemeral, string clientSessionProof)`.
**Data Shape:** `IMemoryCache` entry = the server SECRET ephemeral string under key `LoginEphemeral_<srpIdentity>`; 5-minute TTL. The same initiate→validate choreography is reused for password-change (`change-password/initiate`) and account-deletion flows — hence THREE `cache.Set(...CachePrefixEphemeral + srpIdentity...)` sites in AuthController.cs (:179, :557, :634).

### Decisive source
```csharp
if (!cache.TryGetValue(CachePrefixEphemeral + srpIdentity, out var serverSecretEphemeral) || serverSecretEphemeral is not string)
{
    // No login was initiated for this user, or the server ephemeral has expired. Return false to indicate that no active session was found.
    return (null, false);
}
...
var serverSession = Srp.DeriveSessionServer(serverSecretEphemeral.ToString() ?? string.Empty,
    clientEphemeral, latestVaultEncryptionSettings.Salt, srpIdentity,
    latestVaultEncryptionSettings.Verifier, clientSessionProof);
// If validation failed, serverSession will be null here.
return (serverSession, true);
```

**Flow:** Login stores secret → Validate fetches by identity → `DeriveSessionServer` returns null on proof mismatch → caller branches: `activeSessionFound == false` means expired/never-initiated (NO lockout increment), `true + null session` means wrong password (`userManager.AccessFailedAsync(user)` toward lockout) — the two-way discriminator appears 2× in AuthController.cs (:1052-1059) and 1× in VaultController.cs (:253-260).
**Invariants:** (1) Cache key is srpIdentity, not username, so renames can't orphan in-flight logins and multi-client initiates don't collide across users. (2) A missing entry NEVER counts as a failed password attempt — otherwise cache eviction would lock users out. (3) The ephemeral secret is single-use in practice: any subsequent initiate overwrites it.
**Probe:** `grep -c 'CachePrefixEphemeral + srpIdentity' apps/server/AliasVault.Api/Controllers/AuthController.cs` → `3`; `grep -c 'TimeSpan.FromMinutes(5)' apps/server/AliasVault.Api/Controllers/AuthController.cs` → `3`; `grep -rc 'activeSessionFound ? AuthFailureReason.InvalidPassword : AuthFailureReason.SrpSessionNotFound' apps/server/AliasVault.Api/Controllers/AuthController.cs apps/server/AliasVault.Api/Controllers/VaultController.cs` → `AuthController.cs:2` + `VaultController.cs:1`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-aliasvault", query: "ValidateSrpSession", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt identity-keyed short-TTL ephemeral cache with the active-session/wrong-password discriminator; adapt IMemoryCache to your cache; omit the .NET SecureRemotePassword specifics. Source confirmed at pin `95903e92`; no dedicated unit test covers ValidateSrpSession (coverage caveat).
