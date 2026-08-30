<!-- capsule-v2 -->
# Type-switch payload re-deserialization router — how do I route one JSON envelope stream to per-family typed handlers without a dispatcher framework?

**Source:** Bitwarden server AGPL-3.0 `main@ac309aa19ed351406a56032d5f26a7a9a99f4abd`; Codebase Memory `server`. **Question:** Given a string of JSON whose payload type varies by message type, how do I fan it to the right SignalR destination safely?

## HubHelpers
**Path/Symbol:** `src/Notifications/HubHelpers.cs:20–278` (`SendNotificationToHubAsync`), private handler `policyChangedNotificationHandler` :280–294; truth table `test/Notifications.Test/HubHelpersTest.cs:16–329`.
**Signature:** `public async Task SendNotificationToHubAsync(string notificationJson, CancellationToken cancellationToken = default)`.
**Data Shape:** envelope `{ Type: PushType, ContextId?, Payload: object }`; one payload DTO family per PushType group (e.g. `SyncCipherPushNotification`, `SyncFolderPushNotification`, `AuthRequestPushNotification`, `NotificationPushNotification`); deserializer options `{ PropertyNameCaseInsensitive = true }`.

### Decisive source
```csharp
var notification = JsonSerializer.Deserialize<PushNotificationData<object>>(notificationJson, _deserializerOptions);
if (notification is null) { return; }
switch (notification.Type)
{
    case PushType.SyncCipherUpdate:
    case PushType.SyncCipherCreate:
    case PushType.SyncCipherDelete:
    case PushType.SyncLoginDelete:
        var cipherNotification = JsonSerializer.Deserialize<PushNotificationData<SyncCipherPushNotification>>(notificationJson, _deserializerOptions);
        if (cipherNotification is null) { break; }
        if (cipherNotification.Payload.UserId.HasValue)
            await _hubContext.Clients.User(cipherNotification.Payload.UserId.Value.ToString()).SendAsync(_receiveMessageMethod, cipherNotification, cancellationToken);
        else if (cipherNotification.Payload.OrganizationId.HasValue)
            await _hubContext.Clients.Group(NotificationsHub.GetOrganizationGroup(cipherNotification.Payload.OrganizationId.Value)).SendAsync(_receiveMessageMethod, cipherNotification, cancellationToken);
        break;
    case PushType.AuthRequestResponse:
        // … re-deserialize as AuthRequestPushNotification …
        await _anonymousHubContext.Clients.Group(authRequestResponseNotification.Payload.Id.ToString())
            .SendAsync("AuthRequestResponseRecieved", authRequestResponseNotification, cancellationToken);
        break;
    default:
        _logger.LogWarning("Notification type '{NotificationType}' has not been registered in HubHelpers and will not be pushed as as result", notification.Type);
        break;
}
```

**Flow:** deserialize once against an `<object>` payload just to read the discriminator, then RE-deserialize the same raw JSON into the family's concrete payload type inside each case. Routing is decided from INNER payload fields, with a fixed precedence: user id ⇒ `Clients.User`; else organization id ⇒ organization group; the `Notification/NotificationStatus` family adds Installation first and a client-type split on User (`ClientType.All` ⇒ `Clients.User`, specific type ⇒ `UserClientType_` group). One family escapes the authenticated hub entirely: AuthRequestResponse goes to the anonymous hub under group = payload id, invoking the hub method `"AuthRequestResponseRecieved"` — misspelling included; it is part of the wire contract clients already ship. Unknown types log a warning and are DROPPED, never thrown.
**Invariant:** (1) the envelope-level peek + per-case re-deserialization keeps one parse for routing and one for typing without a polymorphic serializer setup; (2) unresolvable targets (no user/org/installation fields) fall through every branch silently — delivery is best-effort, never an error surface back to the queue; (3) adding a new PushType requires touching this switch or it vanishes into the default-drop with only a log line (deliberate forward-compatibility posture); (4) global messages with no target identifiers send nothing (test-pinned).
**Probe:** `test/Notifications.Test/HubHelpersTest.cs:22–40` pins Global⇒nothing-sent; :44–99 pin Installation groups incl. per-client-type variants; :141–168 pin `UserClientType_{userId}_{t}` vs `Clients.User` on ClientType.All (:104–130); negative `Received(0)` assertions cover BOTH hub contexts in every row.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.trace_path({ project: "server", function_name: "policyChangedNotificationHandler", direction: "inbound", depth: 1 });
```

## Verdict
Adopt: discriminator-peek then typed-reparse pattern; inner-field routing precedence ladder; drop-with-warning default for unknown types; anonymous-hub escape hatch keyed by payload id for pre-auth flows. Adapt: replace the switch with envelope-level target fields when you can (Bitwarden itself documents this as its migration goal — see dual-dialect-wire-contract-tables). Omit: PushType enum values and the typo'd hub-method name.
