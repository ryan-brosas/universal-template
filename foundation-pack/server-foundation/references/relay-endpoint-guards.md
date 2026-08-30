<!-- capsule-v2 -->
# Self-host relay endpoint guards — what must the cloud-side receive endpoint of a self-host→cloud push relay enforce?

**Source:** Bitwarden server AGPL-3.0 `main@ac309aa19ed351406a56032d5f26a7a9a99f4abd`; Codebase Memory `server`. **Question:** How do I accept relayed pushes from thousands of untrusted installations without letting one impersonate another's users?

## Relay receive plane
**Path/Symbol:** `src/Api/Platform/Push/Controllers/PushController.cs:23–158` (`SendAsync` :70–117, `Prefix` :120–130, `CanUse`/`CheckUsage` :132–158); wire model in `src/Core/Models/Api/Request/PushSendRequestModel.cs:7–28`.
**Signature:** `[HttpPost("send")] Task SendAsync([FromBody] PushSendRequestModel<JsonElement> model)`; controller-level `[Route("push")] [Authorize("Push")] [SelfHosted(NotSelfHostedOnly = true)]`.
**Data Shape:** authenticated principal carries the installation id (`_currentContext.InstallationId`); body has nullable UserId/OrganizationId/InstallationId (at least one required), Type, Payload, Identifier, DeviceId, ClientType.

### Decisive source
```csharp
if (model.InstallationId.HasValue)
{
    if (_currentContext.InstallationId!.Value != model.InstallationId.Value)
    {
        throw new BadRequestException("InstallationId does not match current context.");
    }
    target = NotificationTarget.Installation;
    targetId = _currentContext.InstallationId.Value;
}
else if (model.UserId.HasValue)      { target = NotificationTarget.User; ... }
else if (model.OrganizationId.HasValue) { target = NotificationTarget.Organization; ... }
else { throw new UnreachableException("Model validation should have prevented getting here."); }
```
```csharp
private string Prefix(string value) => string.IsNullOrWhiteSpace(value)
    ? null : $"{_currentContext.InstallationId!.Value}_{value}";
// CanUse(): dev bypass, else InstallationId present && !_globalSettings.SelfHosted
```

**Flow:** every registration/delete/add-org/delete-org call re-namespaces ALL inbound identifiers through `Prefix()` (`{installationId}_`) before they reach hub tags — this is what makes the relayed tag grammar in hub-tag-grammar collision-safe. For sends, the target trichotomy is Installation > User > Org; an Installation target MUST equal the authenticated installation (explicit 400 otherwise); the final `else` is UnreachableException because `PushSendRequestModel.Validate` already enforces at-least-one-of.
**Invariant:** (1) the endpoint exists only in the cloud deployment (`NotSelfHostedOnly` + non-SelfHosted check; dev bypass for local work); (2) an installation can never address another installation's ids — everything it supplies is prefixed with ITS OWN authenticated installation id, and the only unprefixed path (Installation target) is equality-checked against the token; (3) validation and controller agree on exactly-one-of so the unreachable branch stays unreachable.
**Probe:** `test/Core.Test/Models/Api/Request/PushSendRequestModelTests.cs:12–140` pins the at-least-one-of validator; `test/Api.IntegrationTest/Platform/Controllers/PushControllerTests.cs` read FULL-RANGE (:21–494, pass 2): the fixture obtains a REAL OAuth token from Identity via client_credentials `client_id=installation.{id}` / `client_secret=installation.Key` / `scope=api.push` (:104–110) — the auth scheme is not mocked; `Send_Works` theory (:381–420) asserts relayed notifications NEVER enter the Azure Queue (`queueClient.Received(0).SendMessageAsync`) and every relay upserts `InstallationDeviceEntity(PartitionKey = installation.Id, RowKey = DeviceId)` so the cloud can later target that device; tag expressions are byte-pinned with the `{installationId}_` prefix, e.g. `(template:payload_userId:%installation%_{userId})`, `(template:payload && organizationId:%installation%_{orgId})`, and Installation targets get `(template:payload && installationId:{id} && clientType:Web)` (:466); error bodies are exact strings — `"InstallationId does not match current context."` (:439) and `"The model state is invalid."` for the no-target row (:492). Sender side: `src/Core/Platform/Push/Engines/RelayPushEngine.cs:43–77` builds `PushSendRequestModel` with identity `installation.{id}` + installation key against `globalSettings.PushRelayBaseUri`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "server", query: "PushController Prefix CheckUsage NotSelfHostedOnly push/send", limit: 10, fields: ["signature", "lines"] });
```

## Verdict
Adopt: identifier namespacing with the authenticated sender id; explicit cross-tenant equality rejection; validator-backed unreachable fallback; deployment-posture gating on the route itself. Adapt: auth scheme (Bitwarden uses client-credentials-style installation identity via BaseIdentityClientService). Omit: the specific Push authorization-policy wiring in ASP.NET startup.
