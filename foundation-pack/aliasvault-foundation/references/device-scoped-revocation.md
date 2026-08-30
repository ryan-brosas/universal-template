<!-- capsule-v2 -->
# Device-scoped session revocation — how do logout and password change avoid nuking every client?

**Source:** aliasvault AGPL-3.0 (patterns-only) `main@95903e926f757046ef32feb7ca147900de0a6802`; Codebase Memory `ext-aliasvault`. **Question:** What composes the device identifier, and which three revocation scopes exist?

## Device identifier composition
**Path/Symbol:** `apps/server/AliasVault.Api/Helpers/AuthHelper.cs:101-119` (`GenerateDeviceIdentifier`).
**Signature:** `string GenerateDeviceIdentifier(HttpRequest request)` — `client|userAgent|acceptLanguage` (+ optional `|appInstanceId` from `X-AliasVault-AppInstanceId`, Android multi-profile).
**Data Shape:** `ClientHeaderInfo.Parse(request.Headers["X-AliasVault-Client"])` yields client name (web/extension/android/ios); parts joined with `'|'`; examples in doc comment: `"chrome|Mozilla/5.0...|en-US"`, `"android|Dalvik/2.1.0...|en-US|550e840e..."`.

### Decisive source
```csharp
// NOTE: This implementation ensures only one refresh token can be valid for a
// specific user/device combo at a time.
List<string?> parts = [clientInfo.ClientName, request.Headers.UserAgent.ToString(),
                       request.Headers.AcceptLanguage.ToString()];
if (appInstanceInfo.AppInstanceId is not null) { parts.Add(appInstanceInfo.AppInstanceId); }
return string.Join('|', parts);
```

**Flow:** logout (`Auth/revoke`, AuthController.cs:403-404) deletes the presented token AND all tokens sharing the device identifier → `revoke-token` (:418-444) deletes ONLY the one row (mobile unlock swap) → password change (`VaultController.UpdateChangePassword`:321-322) force-revokes everything EXCEPT the current device via `ExecuteDeleteAsync`.
**Invariants:** (1) Client-type inclusion is deliberate: logging out of the extension must not kill the web-app session on the same browser. (2) Both "not-found token" endpoints return Ok() to avoid leaking token validity (:391-396, :432-437). (3) Password-change logout is a single SQL set-delete keyed on `x.DeviceIdentifier != deviceIdentifier` — the acting device keeps its fresh-password session.
**Probe:** `grep -c 't.Value == model.RefreshToken || t.DeviceIdentifier == deviceIdentifier' apps/server/AliasVault.Api/Controllers/AuthController.cs` → `1`; `grep -c 'x.DeviceIdentifier != deviceIdentifier' apps/server/AliasVault.Api/Controllers/VaultController.cs` → `1`; `grep -c "return string.Join('|', parts)" apps/server/AliasVault.Api/Helpers/AuthHelper.cs` → `1`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-aliasvault", query: "GenerateDeviceIdentifier", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt header-composed device identity + three revocation scopes; adapt header names to your clients; omit ASP.NET header parsing details. Source confirmed at pin `95903e92`.
