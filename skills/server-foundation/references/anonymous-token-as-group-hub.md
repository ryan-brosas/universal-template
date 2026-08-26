<!-- capsule-v2 -->
# Anonymous token-as-group hub — how do pre-auth clients wait for a server event without accounts or sessions?

**Source:** Bitwarden server AGPL-3.0 `main@ac309aa19ed351406a56032d5f26a7a9a99f4abd`; Codebase Memory `server`. **Question:** How does an unauthenticated device (pending auth request) receive a real-time response?

## AnonymousNotificationsHub
**Path/Symbol:** `src/Notifications/AnonymousNotificationsHub.cs:9–22`; producer side `src/Notifications/HubHelpers.cs` (`PushType.AuthRequestResponse` case, `_anonymousHubContext.Clients.Group(payload.Id)`); wiring `src/Notifications/Startup.cs:29–46` ("Internal" policy) and :49–55.
**Signature:** `[AllowAnonymous] public class AnonymousNotificationsHub : Hub, INotificationHub`.
**Data Shape:** connection URL query parameter `Token`; group name = the raw token value; single hub method `"AuthRequestResponseRecieved"` carrying `PushNotificationData<AuthRequestPushNotification>`.

### Decisive source
```csharp
[AllowAnonymous]
public class AnonymousNotificationsHub : Microsoft.AspNetCore.SignalR.Hub, INotificationHub
{
    public override async Task OnConnectedAsync()
    {
        var httpContext = Context.GetHttpContext();
        var token = httpContext.Request.Query["Token"].FirstOrDefault();
        if (!string.IsNullOrWhiteSpace(token))
        {
            await Groups.AddToGroupAsync(Context.ConnectionId, token);
        }
        await base.OnConnectedAsync();
    }
}
```

**Flow:** a device that has NOT logged in opens the anonymous hub passing its pending auth-request id as the `Token` query value; connect adds the connection to a group literally named by that token. When someone answers the auth request, the authenticated pipeline routes `AuthRequestResponse` to `_anonymousHubContext.Clients.Group(authRequestId)` with the (misspelled, wire-frozen) method name. No membership check, no expiry, no per-connection state beyond the group join; a blank token simply joins nothing and the connection idles.
**Invariant:** (1) the group namespace IS the capability — knowing the auth-request id is what lets you listen, which works because ids are unguessable GUIDs minted server-side; (2) the hub is receive-only from the client's perspective (no invoked hub methods), so there is no write surface to authorize; (3) absence of a token degrades to a no-op connection instead of rejecting — fail-open on join, fail-silent on send; (4) this plane deliberately bypasses every client-type/group grammar used by the authenticated hub.
**Probe:** routing into this hub is contract-pinned end-to-end in `test/Notifications.Test/PostSendEndpointTests.cs:101–103` (literal `{"type":16,…}` case with `ExpectedAnonymousGroup = _authRequestId`) and asserted at :173–176 (`_factory.AnonymousHubClients.Received(1).Group(expectedAnonymousGroup!)`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "server", query: "AnonymousNotificationsHub Token group AuthRequestResponse", limit: 10 });
```

## Verdict
Adopt: token-as-group pattern for short-lived pre-auth waits where the token is a server-minted unguessable id; keep the hub read-only so anonymity stays safe. Adapt: add token validation/expiry if your tokens are user-supplied or long-lived — Bitwarden gets away with raw group names only because of GUID entropy and short lifetimes. Omit: the specific auth-request flow semantics.
