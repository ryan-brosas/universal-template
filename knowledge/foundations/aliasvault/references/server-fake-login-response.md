<!-- capsule-v2 -->
# Server fake login response — how does the API answer unknown users without leaking their existence?

**Source:** aliasvault AGPL-3.0 (patterns-only) `main@95903e926f757046ef32feb7ca147900de0a6802`; Codebase Memory `ext-aliasvault`. **Question:** What must a login-initiate endpoint return for a non-existent user so timing and response shape match the real path?

## Fake SRP data with 4-hour cache
**Path/Symbol:** `apps/server/AliasVault.Api/Controllers/AuthController.cs:1218-1246` (`FakeLoginResponse`), call site :151.
**Signature:** `private OkObjectResult FakeLoginResponse(LoginInitiateRequest model)` → same `LoginInitiateResponse` shape as real users.
**Data Shape:** `(string Salt, string Verifier)` tuple cached in `IMemoryCache` under `AuthHelper.CachePrefixFakeData + model.Username` for `TimeSpan.FromHours(4)`; response carries `Defaults.EncryptionType`/`Defaults.EncryptionSettings` (the shared client defaults) and NO `srpIdentity` field.

### Decisive source
```csharp
// Try to get cached fake data first
if (!cache.TryGetValue(fakeDataCacheKey, out (string Salt, string Verifier) fakeData))
{
    // Generate new fake data if not cached
    var client = new SrpClient();
    var fakeSalt = client.GenerateSalt();
    var fakePrivateKey = client.DerivePrivateKey(fakeSalt, model.Username, "fakePassword");
    var fakeVerifier = client.DeriveVerifier(fakePrivateKey);
    fakeData = (fakeSalt, fakeVerifier);
    cache.Set(fakeDataCacheKey, fakeData, TimeSpan.FromHours(4));
}
// Always generate a new ephemeral for the fake data, as this is also done for existing users.
var fakeEphemeral = Srp.GenerateEphemeralServer(fakeData.Verifier);
```

**Flow:** Login() finds no user → logs `AuthFailureReason.InvalidUsername` internally → returns `FakeLoginResponse(model)` with HTTP 200 → client performs full SRP math against the fake verifier and always fails at validate (proof mismatch), indistinguishable from a wrong password.
**Invariants:** (1) The fake EPHEMERAL is regenerated per request exactly like the real path (timing parity); only salt+verifier are cached. (2) Fake verifier derives from constant `"fakePassword"` — deterministic per username but cryptographically useless. (3) Response omits `srpIdentity`, which real responses include — clients fall back to normalized username (see srp-identity-vs-username capsule), keeping the flow alive without revealing why. (4) Failure at validate maps BOTH unknown-user and bad-password to the same generic error (`USER_NOT_FOUND` :1060).
**Probe:** `grep -c 'return FakeLoginResponse(model);' apps/server/AliasVault.Api/Controllers/AuthController.cs` → `1`; `grep -c 'private OkObjectResult FakeLoginResponse(' apps/server/AliasVault.Api/Controllers/AuthController.cs` → `1`; `grep -c 'Defaults.EncryptionType,' apps/server/AliasVault.Api/Controllers/AuthController.cs` → `1` (only the fake path); `grep -c 'TimeSpan.FromHours(4)' apps/server/AliasVault.Api/Controllers/AuthController.cs` → `1`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-aliasvault", query: "FakeLoginResponse", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt cached-fake-verifier + fresh-ephemeral + identical-envelope anti-enumeration; adapt cache backend; omit SpamOK-specific defaults. Source confirmed at pin `95903e92`; no dedicated upstream test file covers this method (coverage caveat).
