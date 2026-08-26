<!-- capsule-v2 -->
# Alias-claim sync with silent rate-limit skip — how are user email claims reconciled when vault uploads declare addresses?

**Source:** aliasvault AGPL-3.0 (patterns-only) `main@95903e926f757046ef32feb7ca147900de0a6802`; Codebase Memory `ext-aliasvault`. **Question:** What is the claim lifecycle (add/re-enable/disable) and how do creation limits behave at the boundary?

## Claim reconciliation
**Path/Symbol:** `apps/server/AliasVault.Api/Controllers/VaultController.cs:375-514` (`UpdateUserEmailClaims`), limits via `rateLimitService.ResolveAsync(user, RateLimitType.AliasCreation)` :393.
**Signature:** `Task UpdateUserEmailClaims(AliasServerDbContext context, AliasVaultUser user, List<string> newEmailAddresses)` — called from Update() only when `model.EmailAddressList.Count > 0`.
**Data Shape:** `UserEmailClaim { UserId, Address, AddressLocal, AddressDomain, Disabled, CreatedAt, UpdatedAt }`; claims are NEVER deleted ("Email claims are considered permanent", :500-502).

### Decisive source
```csharp
// Calculate the current usage baseline per limit. addedThisSync is then added to each in the loop.
int baseCount;
if (limit.WindowSeconds == 0) {
    // Global absolute cap: every claim the user has ever made (including disabled ones).
    baseCount = userOwnedEmailClaims.Count;
} else {
    // Time-based cap: aliases created within the rolling window (create-then-delete still counts).
    baseCount = await context.UserEmailClaims.CountAsync(x => x.UserId == user.Id && x.CreatedAt >= windowStart);
}
...
// Once any limit is reached, silently skip creating further aliases (logged once for audits).
if (limitUsages.Any(u => u.BaseCount + addedThisSync >= u.MaxCount)) { ...; continue; }
```

**Flow:** sanitize+dedupe input → per-address ladder: invalid format skip → unsupported-domain skip → own-existing claim: re-enable if Disabled else no-op → foreign claim: log-and-skip → limit gate (`base + addedThisSync >= max`, ANY limit trips) → insert. Afterwards, owned-but-no-longer-declared claims get `Disabled = true` (never removed).
**Invariants:** (1) Limits SKIP silently rather than failing the vault save — one over-limit alias never blocks the whole sync; a single warn is logged per request (`aliasLimitLogged` latch). (2) `addedThisSync` counts within-request additions so a batch can't sneak N creations past a limit with room for one. (3) Global caps count DISABLED claims too — disabling doesn't reset quotas. (4) Foreign-claim collisions are logged warnings, not errors; uniqueness is enforced by DB constraint with DbUpdateException caught per-row.
**Probe:** `grep -c 'addedThisSync' apps/server/AliasVault.Api/Controllers/VaultController.cs` → `4`; `grep -c 'aliasLimitLogged' apps/server/AliasVault.Api/Controllers/VaultController.cs` → `3`; `grep -c 'existingUserClaim.Disabled = false' apps/server/AliasVault.Api/Controllers/VaultController.cs` → `1`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-aliasvault", query: "UpdateUserEmailClaims", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt permanent-claims reconciliation with silent per-row skips and additive in-batch counting; adapt limit config; omit EF Core specifics. Source confirmed at pin `95903e92`.
