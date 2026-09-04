<!-- capsule-v2 -->
# Hub group grammar + connect lifecycle — how do I put a SignalR connection into exactly the broadcast groups its authenticated user can hear?

**Source:** Bitwarden server AGPL-3.0 `main@ac309aa19ed351406a56032d5f26a7a9a99f4abd`; Codebase Memory `server`. **Question:** When a client connects to the real-time hub, which groups does it join, who names them, and how does disconnect stay consistent?

## NotificationsHub
**Path/Symbol:** `src/Notifications/NotificationsHub.cs:12–118` (`OnConnectedAsync`, `OnDisconnectedAsync`, static `GetUserGroup/GetOrganizationGroup/GetInstallationGroup`); `src/Notifications/SubjectUserIdProvider.cs:9–15`; wiring `src/Notifications/Startup.cs:47–66`.
**Signature:** `public override async Task OnConnectedAsync()` / `OnDisconnectedAsync(Exception)`; `public static string GetOrganizationGroup(Guid organizationId, ClientType? clientType = null)`.
**Data Shape:** group-name strings: `UserClientType_{userId}_{clientType}` (user groups are ALWAYS client-type-scoped — there is no plain `User_` group), `Organization_{orgId}` / `OrganizationClientType_{orgId}_{t}`, `Installation_{id}` / `Installation_ClientType_{id}_{t}`. Connection identity: `SubjectUserIdProvider.GetUserId` returns the JWT `sub` claim, so `Clients.User(id)` works without any group.

### Decisive source
```csharp
public override async Task OnConnectedAsync()
{
    var currentContext = new CurrentContext(null, null);
    await currentContext.BuildAsync(Context.User, _globalSettings);

    var clientType = DeviceTypes.ToClientType(currentContext.DeviceType);
    if (clientType != ClientType.All && currentContext.UserId.HasValue)
    {
        await Groups.AddToGroupAsync(Context.ConnectionId, GetUserGroup(currentContext.UserId.Value, clientType));
    }
    if (_globalSettings.Installation.Id != Guid.Empty)
    {
        await Groups.AddToGroupAsync(Context.ConnectionId, GetInstallationGroup(_globalSettings.Installation.Id));
    }
    // … same pattern for every org in currentContext.Organizations …
    _connectionCounter.Increment();
    await base.OnConnectedAsync();
}
```

**Flow:** every connect AND disconnect event rebuilds a fresh `CurrentContext` from the connection's claims (`BuildAsync(Context.User, …)` — no caching across events), derives `ClientType` from the device type, then symmetrically adds/removes the identical group set: per-client-type user group (only when client type is specific and a user id exists), installation All+specific groups (only when this deployment has an installation id ≠ Empty), and for each org membership an All group plus a specific-client-type group. A process-wide singleton `ConnectionCounter` brackets the session with Interlocked Inc/Dec.
**Invariant:** (1) connect/disconnect are exact mirrors — the same predicate computes the same group names on both sides, so membership can never leak; (2) group names come from ONE place (static builders shared with producers and tests), never string-interpolated at call sites; (3) unauthenticated/unresolvable context ⇒ connection stays open but joins nothing (fail-closed by omission); (4) `Clients.User(...)` needs no group because the user-id provider reads `sub` — reserve groups for scoping axes beyond identity (client type, org, installation).
**Probe:** byte-exact group names pinned in `test/Notifications.Test/HubHelpersTest.cs:59` (`$"Installation_{id}"`), `:90` (`Installation_ClientType_{id}_{t}`), `:159` (`UserClientType_{userId}_{t}`), `:187/:218` (`Organization_{id}` / `OrganizationClientType_{id}_{t}`); negative rows assert zero sends when Global=true with no target (:22–40).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "server", query: "NotificationsHub OnConnectedAsync GetUserGroup OrganizationClientType", limit: 10 });
```

## Verdict
Adopt: static group-name builders as the single naming authority; claim-rebuild-per-event with mirrored add/remove; client-type as a second axis baked into group names rather than filtered post-delivery; `sub`-claim user-id provider for direct user addressing. Adapt: the counter to your metrics story (it feeds a periodic log job only). Omit: Bitwarden's CurrentContext claim schema specifics.
