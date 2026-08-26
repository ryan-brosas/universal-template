<!-- capsule-v2 -->
# Notification-hub tag grammar — how do template tags express target, exclusion, and client type on the send path?

**Source:** Bitwarden server AGPL-3.0 `main@ac309aa19ed351406a56032d5f26a7a9a99f4abd`; Codebase Memory `server`. **Question:** What exact tag expression reaches the hub for each target kind, and how is the originating device excluded?

## Send-path tag builder
**Path/Symbol:** `src/Core/Platform/Push/NotificationHub/NotificationHubPushEngine.cs:58–93` (`BuildTag`, `PushAsync`), `:139–147` (`SanitizeTagInput`), template side in `src/Core/Platform/PushRegistration/NotificationHubPushRegistrationService.cs:233–258` (`BuildInstallationTemplate`).
**Signature:** `string BuildTag(string tag, string? identifier, ClientType? clientType)`.
**Data Shape:** send payload is a template dictionary `{ "type": ((byte)pushType).ToString(), "payload": JsonSerializer.Serialize(payload) }`; tags are Azure Notification Hub tag expressions joined by `&&`.

### Decisive source
```csharp
private string BuildTag(string tag, string? identifier, ClientType? clientType)
{
    if (!string.IsNullOrWhiteSpace(identifier))
    {
        tag += $" && !deviceIdentifier:{SanitizeTagInput(identifier)}";
    }
    if (clientType.HasValue && clientType.Value != ClientType.All)
    {
        tag += $" && clientType:{clientType}";
    }
    return $"({tag})";
}
// PushAsync initial tag by Target:
//   User          => $"template:payload_userId:{TargetId}"
//   Organization  => $"template:payload && organizationId:{TargetId}"
//   Installation  => $"template:payload && installationId:{TargetId}"
```

**Flow:** target switch builds the base expression (user targets ride the per-user *template name* `template:payload_userId:{id}` registered on that user's installations; org/installation target the shared `template:payload` template filtered by tag) → exclusion clause appends `&& !deviceIdentifier:{sanitized}` only when ExcludeCurrentContext resolved a live device identifier → clientType clause appended unless null or All → whole expression wrapped in parentheses.
**Invariant:** (1) exclusion is NEGATIVE-match on the raw device identifier, sanitized to `[a-zA-Z0-9-_:]` before interpolation — unsanitized input could inject tag-expression operators; (2) `ClientType.All` emits NO clause (do not emit `clientType:All`); (3) relayed notifications reuse the same grammar but every user/org id is prefixed `{fromInstallation}_` to avoid cross-installation collisions, and installation-target relays use the bare installationId.
**Probe:** `test/Core.Test/Platform/Push/NotificationHub/NotificationHubPushEngineTests.cs:20–101` — byte-exact asserts: `(template:payload_userId:{userId} && !deviceIdentifier:test_device_identifier)`, org `(template:payload && organizationId:{orgId} && !deviceIdentifier:…)`, installation twin, and envelope asserts `dict["type"] == ((byte)PushType.SyncCiphers).ToString()`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "server", query: "BuildTag SanitizeTagInput template:payload_userId", limit: 10, fields: ["signature", "lines"] });
```

## Verdict
Adopt: parenthesized AND-of-clauses grammar; negative deviceIdentifier exclusion; enum-default elision; identifier sanitization whitelist. Adapt: tag operator syntax to your broker's filtering language (the structure transfers even if `&&`/`!` spellings differ). Omit: Azure template-registration mechanics themselves (see registration-templates-tag-patch).
