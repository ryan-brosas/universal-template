<!-- capsule-v2 -->
# Vault retention rule union — which backups survive when every save appends a full blob?

**Source:** aliasvault AGPL-3.0 (patterns-only) `main@95903e926f757046ef32feb7ca147900de0a6802`; Codebase Memory `ext-aliasvault`. **Question:** Given append-only vault rows, what deletion policy keeps enough history to roll back without unbounded growth?

## Six-rule keep-set union
**Path/Symbol:** `apps/server/AliasVault.Api/Controllers/VaultController.cs:49-60` (policy literal), `apps/server/AliasVault.Api/Vault/VaultRetentionManager.cs:30-64` (`ApplyRetention`), rules under `AliasVault.Api/Vault/RetentionRules/`.
**Signature:** `List<Vault> ApplyRetention(RetentionPolicy retentionPolicy, List<Vault> existingVaults, DateTime now, Vault? newVault = null)`.
**Data Shape:** Rules: Revision×3, Daily×2, Weekly×1, Monthly×1, DbVersion×2, LoginCredential×2. Each rule returns its OWN keep list; the union is a `HashSet<Vault>`; everything else is deleted.

### Decisive source
```csharp
foreach (var rule in retentionPolicy.Rules)
{
    var keptVaults = rule.ApplyRule(existingVaults, now);
    foreach (var vault in keptVaults) { vaultsToKeep.Add(vault); }
}
// Always keep the most recent vault
if (existingVaults.Count > 0) { vaultsToKeep.Add(existingVaults[0]); }
```
```csharp
// RevisionRetentionRule — last vault per revision number, newest N revisions
return vaults.GroupBy(x => x.RevisionNumber)
    .Select(g => g.OrderByDescending(x => x.UpdatedAt).First())
    .OrderByDescending(x => x.UpdatedAt).Take(RevisionsToKeep);
// DailyRetentionRule groups by x.UpdatedAt.Date; DbVersionRetentionRule by x.Version
```

**Flow:** new vault arrives → caller pre-projects EXISTING rows WITHOUT blobs (`VaultBlob = string.Empty` projection, :338-360) → manager appends the new row virtually → sorts by UpdatedAt desc → each rule marks keeps → unmarked rows are RemoveRange'd in the same DbContext save as the insert.
**Invariants:** (1) The most recent vault is ALWAYS kept regardless of rules. (2) Rules are unions, not intersections — a vault surviving ANY rule is safe. (3) Grouping keys differ per rule (revision / day / week / month / app version / login credential); "last per group" then global Take(N). (4) Blob columns are never loaded for the deletion decision — only metadata.
**Probe:** `grep -c 'new .*RetentionRule {' apps/server/AliasVault.Api/Controllers/VaultController.cs` → `6`; `grep -c 'GroupBy(x => x.RevisionNumber)' apps/server/AliasVault.Api/Vault/RetentionRules/RevisionRetentionRule.cs` → `1`; `grep -c 'GroupBy(x => x.UpdatedAt.Date)' apps/server/AliasVault.Api/Vault/RetentionRules/DailyRetentionRule.cs` → `1`; `grep -c 'GroupBy(x => x.Version)' apps/server/AliasVault.Api/Vault/RetentionRules/DbVersionRetentionRule.cs` → `1`; `grep -c 'vaultsToKeep.Add(existingVaults\[0\])' apps/server/AliasVault.Api/Vault/VaultRetentionManager.cs` → `1`.

## Direct tests
**Path/Symbol:** `apps/server/Tests/AliasVault.UnitTests/Vault/RetentionManager/GeneralRetentionTests.cs` (upstream NUnit coverage of ApplyRetention).
**Probe:** run upstream suite where dotnet is available; deterministic probes above pin the rule shape at pin `95903e92`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-aliasvault", query: "ApplyRetention", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt grouped-rule union retention with metadata-only pre-projection; adapt rule counts to product needs; omit ASP.NET/EF specifics. Upstream unit tests exist (GeneralRetentionTests.cs) but were not executed in this environment.
