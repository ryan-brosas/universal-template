<!-- capsule-v2 -->
# Vault revision optimistic concurrency — how does the server arbitrate whole-blob uploads from multiple clients?

**Source:** aliasvault AGPL-3.0 (patterns-only) `main@95903e926f757046ef32feb7ca147900de0a6802`; Codebase Memory `ext-aliasvault`. **Question:** What is the exact accept/outdated ladder for a POSTed vault blob, and which fields are inherited from the previous revision?

## Revision-number gate
**Path/Symbol:** `apps/server/AliasVault.Api/Controllers/VaultController.cs:137-219` (`Update`), gate at :164-178; same gate in `UpdateChangePassword` :264-284.
**Signature:** `POST v1/Vault` body `Vault { Username, Blob, Version, CurrentRevisionNumber, CredentialsCount, EmailAddressList, EncryptionPublicKey }`.
**Data Shape:** Each `AliasServerDb.Vault` row stores the full encrypted blob + `RevisionNumber`, `Salt`, `Verifier`, `EncryptionType`, `EncryptionSettings`, `FileSize` (KB from base64), `Client` header echo. Latest = highest RevisionNumber.

### Decisive source
```csharp
// Reject vaults with a version that is lower than the last vault version.
if (VersionHelper.IsVersionOlder(model.Version, latestVault.Version))
    return BadRequest(... ApiErrorCode.VAULT_NOT_UP_TO_DATE ...);

// Calculate the new revision number for the vault.
var newRevisionNumber = model.CurrentRevisionNumber + 1;
// If so it means the client's vault is outdated and the client should fetch the latest vault
// from the server before saving can continue.
if (latestVault.RevisionNumber >= newRevisionNumber)
    return Ok(new VaultUpdateResponse { Status = VaultStatus.Outdated, NewRevisionNumber = latestVault.RevisionNumber });
```

**Flow:** username match check (:152, multi-tab guard) → version-not-older check (400) → `latest.Revision >= client.Revision + 1` ⇒ HTTP **200** with `Status=Outdated` + server's number (client must merge-and-retry) → else append NEW row inheriting `latestVault.Salt/Verifier/EncryptionType/EncryptionSettings` verbatim → retention manager prunes old rows in the SAME save.
**Invariants:** (1) Vaults are an APPEND-ONLY audit chain — no UPDATE of existing blobs ever happens; "update" inserts a new revision. (2) Outdated is a 200-with-status, NOT an error status code. (3) KDF material can only change through the dedicated `change-password` endpoint, never a normal upload. (4) Both gates run twice in the file — Update and UpdateChangePassword share the ladder shape.
**Probe:** `grep -c 'latestVault.RevisionNumber >= newRevisionNumber' apps/server/AliasVault.Api/Controllers/VaultController.cs` → `2`; `grep -c 'VaultStatus.Outdated' apps/server/AliasVault.Api/Controllers/VaultController.cs` → `2`; `grep -c 'Salt = latestVault.Salt' apps/server/AliasVault.Api/Controllers/VaultController.cs` → `1`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-aliasvault", query: "VaultUpdateResponse", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt append-only revisions + optimistic revision gate with 200-outdated semantics; adapt storage; omit EF Core specifics. Source confirmed at pin `95903e92`; covered indirectly by E2E VaultUpgradeTests (coverage caveat).
