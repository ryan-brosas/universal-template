<!-- capsule-v2 -->
# Mobile QR login handshake — how does a web session mint credentials for the phone without the phone ever typing a password?

**Source:** aliasvault AGPL-3.0 (patterns-only) `main@95903e926f757046ef32feb7ca147900de0a6802`; Codebase Memory `ext-aliasvault`. **Question:** What are the initiate/poll/submit phases, and which database fields guarantee one-time delivery?

## Three-phase request lifecycle
**Path/Symbol:** `apps/server/AliasVault.Api/Controllers/AuthController.cs:649-696` (`InitiateMobileLogin`), :703-796 (`PollMobileLogin`), :826-862 (`SubmitMobileLogin`), timeout const :62 (`MobileLoginTimeoutMinutes = 10`).
**Signature:** POST `Auth/mobile-login/initiate { ClientPublicKey }` → `{ RequestId }`; GET `Auth/mobile-login/poll/{requestId}`; POST `Auth/mobile-login/submit { RequestId, EncryptedDecryptionKey }`.
**Data Shape:** `MobileLoginRequest` row: `Id` (GUID "N"), `ClientPublicKey`, `CreatedAt`, `ClientIpAddress`, then submit fills `EncryptedDecryptionKey`, `UserId`, `FulfilledAt`, `MobileIpAddress`.

### Decisive source
```csharp
// Check if already retrieved (one-time use protection)
if (loginRequest.RetrievedAt != null)
{
    return NotFound(... MOBILE_LOGIN_REQUEST_NOT_FOUND ...);
}
...
// Mark as retrieved and clear sensitive data from database
loginRequest.ClientPublicKey = string.Empty;
loginRequest.EncryptedDecryptionKey = null;
loginRequest.RetrievedAt = timeProvider.UtcNow;
```
```csharp
var encryptedToken = Cryptography.Server.Encryption.SymmetricEncrypt(tokenModel.Token, symmetricKey);
var encryptedRefreshToken = Cryptography.Server.Encryption.SymmetricEncrypt(tokenModel.RefreshToken, symmetricKey);
var encryptedSymmetricKey = Cryptography.Server.Encryption.EncryptSymmetricKeyWithRsa(symmetricKey, loginRequest.ClientPublicKey);
```

**Flow:** browser (anonymous, rate-limited per IP) registers an RSA public key + gets requestId → phone (authenticated via QR deep link carrying requestId) fetches the public key and submits its `EncryptedDecryptionKey` + userId → browser polls: unfulfilled ⇒ `Fulfilled=false` shell; fulfilled ⇒ server wraps access+refresh+username in ONE fresh symmetric key, RSA-wraps that key to the browser's public key, returns all four ciphertexts, marks `RetrievedAt`, wipes public key + decryption key from the row.
**Invariants:** (1) Poll is single-use — second poll of a retrieved request 404s even though tokens were delivered. (2) Expiry (10 min vs client's 2-min countdown = deliberate 3× buffer) is checked at EVERY phase against `CreatedAt`. (3) Submit is once-only too (`FulfilledAt != null ⇒ 400 ALREADY_FULFILLED`) — a stolen QR can't re-fulfill. (4) The vault-decryption key travels phone→server→browser but is nulled out of the DB after retrieval; only ciphertext remains in flight. (5) Sanity gates on poll: user exists, not blocked, not locked out.
**Probe:** unrelated-SRP separation: `grep -c 'CachePrefixEphemeral + srpIdentity' apps/server/AliasVault.Api/Controllers/AuthController.cs` → `3` (the QR plane uses DB rows, never the ephemeral cache); one-time latch: `grep -c 'RetrievedAt' apps/server/AliasVault.Api/Controllers/AuthController.cs` → `2` (check :732 + stamp :782); expiry checks: `grep -c 'AddMinutes(MobileLoginTimeoutMinutes)' apps/server/AliasVault.Api/Controllers/AuthController.cs` → `3` (poll, fetch-key, submit).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-aliasvault", query: "MobileLoginRequest", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the row-carried challenge lifecycle with RetrievedAt/FulfilledAt one-time latches; adapt key wrapping to your crypto stack; omit ASP.NET specifics. Source confirmed at pin `95903e92`; no dedicated unit test file covers these endpoints (coverage caveat).
