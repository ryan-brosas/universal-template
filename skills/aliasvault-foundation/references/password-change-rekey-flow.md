<!-- capsule-v2 -->
# Password-change rekey flow — how do new SRP credentials and a re-encrypted vault commit atomically?

**Source:** aliasvault AGPL-3.0 (patterns-only) `main@95903e926f757046ef32feb7ca147900de0a6802`; Codebase Memory `ext-aliasvault`. **Question:** Why does the change-password submit live in VaultController, and what is the exact proof→revoke ordering?

## Cross-controller choreography
**Path/Symbol:** `apps/server/AliasVault.Api/Controllers/AuthController.cs:536-560` (`InitiatePasswordChange`, route `Auth/change-password/initiate`), `apps/server/AliasVault.Api/Controllers/VaultController.cs:227-325` (`UpdateChangePassword`, route `Vault/change-password`).
**Signature:** initiate → `PasswordChangeInitiateResponse(Salt, Ephemeral.Public, EncryptionType, EncryptionSettings, srpIdentity)`; submit body `VaultPasswordChangeRequest { ..., CurrentClientPublicEphemeral, CurrentClientSessionProof, Blob (re-encrypted), NewPasswordSalt, NewPasswordVerifier }`.
**Data Shape:** The controller XML doc states the split: "the submit handler ... is in VaultController.UpdateChangePassword() because changing the password of the AliasVault user also requires a new vault encrypted with that same password."

### Decisive source
```csharp
// VaultController.cs — new vault row carries the NEW credentials...
Salt = model.NewPasswordSalt,
Verifier = model.NewPasswordVerifier,
EncryptionType = Defaults.EncryptionType,
EncryptionSettings = Defaults.EncryptionSettings,
...
user.PasswordChangedAt = timeProvider.UtcNow;
...
// Force revoke all user logged in sessions except current one.
var deviceIdentifier = AuthHelper.GenerateDeviceIdentifier(Request);
await context.AliasVaultUserRefreshTokens
    .Where(x => x.UserId == user.Id && x.DeviceIdentifier != deviceIdentifier)
    .ExecuteDeleteAsync();
```

**Flow:** initiate validates session-less auth context and caches server ephemeral under srpIdentity (5 min, same cache as login) → client derives old-password proof AND re-encrypts the vault locally with the new password → submit verifies OLD password via `ValidateSrpSession` (wrong proof ⇒ AccessFailedAsync lockout path) → revision gate → insert vault row with NEW salt/verifier + re-encrypted blob → stamp `PasswordChangedAt` → mass-revoke other devices.
**Invariants:** (1) Proof-of-old-password and new-credentials arrive in ONE request — the server never holds both passwords. (2) Revocation happens AFTER the new vault row commits, so the acting device isn't logged out mid-flight. (3) New KDF params are reset to shared defaults on every password change (fresh start for future per-user upgrades). (4) The stale ephemeral cache from initiate is simply overwritten/expired — no explicit cleanup needed.
**Probe:** `grep -c 'Salt = model.NewPasswordSalt' apps/server/AliasVault.Api/Controllers/VaultController.cs` → `1`; `grep -c 'ExecuteDeleteAsync' apps/server/AliasVault.Api/Controllers/VaultController.cs` → `1`; `grep -c 'change-password/initiate' apps/server/AliasVault.Api/Controllers/AuthController.cs` → `1`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-aliasvault", query: "UpdateChangePassword", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt single-request old-proof + new-verifier + re-encrypted blob with post-commit device revocation; adapt routes; omit ASP.NET Identity calls. Source confirmed at pin `95903e92`.
