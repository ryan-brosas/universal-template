<!-- capsule-v2 -->
# Device registration templates & tag patching — how do I register devices across mobile/web platforms and add/remove org membership without rewriting registrations?

**Source:** Bitwarden server AGPL-3.0 `main@ac309aa19ed351406a56032d5f26a7a9a99f4abd`; Codebase Memory `server`. **Question:** What does a correct install registration look like per platform, and how do org membership changes propagate to all of a user's devices cheaply?

## Registration service
**Path/Symbol:** `src/Core/Platform/PushRegistration/NotificationHubPushRegistrationService.cs:17–325` (`CreateOrUpdateRegistrationAsync` :40–81, mobile :83–146, web :148–196, `BuildInstallationTemplate` :233–258, patch :278–313, `GetComb` :315–325).
**Signature:** `Task CreateOrUpdateRegistrationAsync(PushRegistrationData data, string deviceId, string userId, string? identifier, DeviceType type, IEnumerable<string> organizationIds, Guid installationId)` / `Task AddUserRegistrationOrganizationAsync(IEnumerable<string> deviceIds, string organizationId)`.
**Data Shape:** Azure `Installation` keyed by deviceId; tags `userId:{u}`, `clientType:{t}`, optional `deviceIdentifier:{id}`, `installationId:{i}`, one `organizationId:{o}` each; three named templates `template:payload|message|badgeMessage`, each carrying its own mirrored tag set including `{fullTemplateId}_userId:{userId}`.

### Decisive source
```csharp
var operation = new PartialUpdateOperation { Operation = op, Path = "/tags" };
if (op == UpdateOperationType.Add)
{
    operation.Value = tag;                 // ADD: value carries the tag
}
else if (op == UpdateOperationType.Remove)
{
    operation.Path += $"/{tag}";           // REMOVE: tag moves into the PATH
}
// per device: ClientFor(GetComb(deviceId)).PatchInstallationAsync(deviceId, [operation])
// errors: catch (Exception e) when (e.InnerException == null ||
//     !e.InnerException.Message.Contains("(404) Not Found")) { throw; }  // swallow only 404
```
```csharp
if (!string.IsNullOrWhiteSpace(installation.PushChannel)) { /* mobile */ }
else if (data.WebPush != null) { /* browser REST PUT installations/{id}, platform:"browser",
    UnsafeRelaxedJsonEscaping — "Azure SDK is currently lacking support for web push" */ }
if (InstallationDeviceEntity.IsInstallationDeviceId(deviceId))
    await _installationDeviceRepository.UpsertAsync(new InstallationDeviceEntity(deviceId));
```

**Flow:** empty PushToken ⇒ no-op BEFORE any hub call (test asserts `Received(0).ClientFor`); mobile platforms (Android→FcmV1, iOS→Apns, AndroidAmazon→Adm) get exactly 3 platform-specific template bodies; non-mobile device types get ZERO templates (tags-only install); hub selection goes through `GetComb(deviceId)` which strips an `InstallationDeviceEntity` prefix to its RowKey before `Guid.TryParse` (garbage ⇒ `Exception($"Invalid device id {deviceId}.")`); org changes PATCH `/tags` per device instead of GET-modify-PUT of whole installations; missing-device 404s are swallowed so stale devices don't break batch updates.
**Invariant:** (1) ADD vs REMOVE use structurally different JSON-Patch encodings — value-vs-path asymmetry is the API contract, not a bug; (2) template tag sets mirror install tags but ALSO pin the per-user template name suffix (`template:payload_userId:{u}`) consumed by the send-path grammar; (3) only exact "(404) Not Found" inner messages are tolerated — everything else propagates; (4) web-push bypasses the SDK entirely via hand-built SAS request from `NotificationHubConnection.CreateRequest` (`api-version=2015-01`).
**Probe:** `test/Core.Test/Platform/PushRegistration/NotificationHubPushRegistrationServiceTests.cs:18–30` (empty-token no-op), `:32–106` (Android template bodies byte-exact incl. FCM v1 `{"message":{"data":…}}` wrapper), `:108–182` (APNs aps bodies), `:184–258` (ADM), `:260–290` (non-mobile ⇒ `Templates.Count == 0`). Runner caveat recorded at leaf level (dotnet blocked read-only).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "server", query: "PatchTagsForUserDevicesAsync BuildInstallationTemplate CreateOrUpdateRegistrationAsync", limit: 10, fields: ["signature", "lines"] });
```

## Verdict
Adopt: no-op-before-network on missing channel; fixed template trio per mobile platform with mirrored tags; tags-only installs for desktop/web extensions; JSON-Patch tag deltas for membership changes; 404-tolerant batch patching; installation-device entity upsert beside hub state. Adapt: template body spellings to your push providers' payload schemas. Omit: Azure SDK types and the SAS REST fallback if your broker supports web push natively.
