<!-- capsule-v2 -->
# SRP identity vs username — why is the verifier built from a random GUID instead of the login name?

**Source:** aliasvault AGPL-3.0 (patterns-only) `main@95903e926f757046ef32feb7ca147900de0a6802`; Codebase Memory `ext-aliasvault`. **Question:** Which string must feed `srp_derive_private_key` at registration and at every later login, and what happens for legacy accounts?

## Client: GUID identity minted at registration
**Path/Symbol:** `apps/browser-extension/src/utils/auth/SrpAuthService.ts:287-320` (`prepareRegistration`), :267-273 (`generateSrpIdentity` = `crypto.randomUUID()`).
**Signature:** `prepareRegistration(username, password): Promise<RegisterRequest>` where `RegisterRequest = { username, salt, verifier, encryptionType, encryptionSettings, srpIdentity }`.
**Data Shape:** `srpIdentity` is a random GUID generated once at registration, sent to the server, stored on the user row; the verifier is derived with `derivePrivateKey(salt, srpIdentity, credentials.passwordHashString)` — NOT the username (:309).

### Decisive source
```ts
/**
 * Generate a random GUID for SRP identity. This is used for all SRP operations,
 * is set during registration, and never changes.
 */
const srpIdentity = SrpAuthService.generateSrpIdentity();

// Generate SRP private key and verifier using srpIdentity (not username)
const privateKey = await SrpAuthService.derivePrivateKey(salt, srpIdentity, credentials.passwordHashString);
```

**Flow:** login-initiate returns the server's stored `srpIdentity` in `LoginInitiateResponse`; client falls back to normalized username only for pre-GUID accounts — `const srpIdentity = loginResponse.srpIdentity ?? normalizedUsername;` (:422, marked `@todo Remove fallback after 0.26.0+`) → that identity feeds `derivePrivateKey` and `deriveSession`.
**Invariants:** (1) The M1 hash binds `H(I)`, so verifier and session MUST use the same identity string forever — using the typed username after a rename would brick auth; the GUID makes renames safe. (2) Server mirrors the fallback identically: `var srpIdentity = user.SrpIdentity ?? user.UserName!.ToLowerInvariant();` appears 3× in AuthController.cs (Login :172, InitiatePasswordChange :550, InitiateAccountDeletion :627) + 1× in AuthHelper.cs:42 (`ValidateSrpSession`). (3) Registration accepts client-supplied identity or falls back server-side (`model.SrpIdentity ?? model.Username.ToLowerInvariant()`, AuthController.cs:486).
**Probe:** `grep -c 'srpIdentity ?? normalizedUsername' apps/browser-extension/src/utils/auth/SrpAuthService.ts` → `1`; `grep -c 'generateSrpIdentity' apps/browser-extension/src/utils/auth/SrpAuthService.ts` → `2`; `grep -rc 'user.UserName!.ToLowerInvariant()' apps/server/AliasVault.Api/Controllers/AuthController.cs apps/server/AliasVault.Api/Helpers/AuthHelper.cs` → `apps/server/AliasVault.Api/Controllers/AuthController.cs:3` + `apps/server/AliasVault.Api/Helpers/AuthHelper.cs:1`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-aliasvault", query: "srpIdentity", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt immutable-random-identity SRP binding (rename-proof auth); adapt identity generation to host RNG/UUID; omit the legacy-username fallback once your floor version supports GUIDs. Source confirmed at pin `95903e92` both sides of the wire.
