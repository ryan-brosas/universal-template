<!-- capsule-v2 -->
# Dual-dialect wire contract tables — how do I keep a producer→queue/HTTP→consumer notification pipeline format-safe across rolling deploys?

**Source:** Bitwarden server AGPL-3.0 `main@ac309aa19ed351406a56032d5f26a7a9a99f4abd`; Codebase Memory `server`. **Question:** How do I pin the wire formats between push producers and two different ingestion paths so no deploy combination silently breaks routing?

## AzureQueuePipelineTests + PostSendEndpointTests
**Path/Symbol:** `test/Notifications.Test/AzureQueuePipelineTests.cs:38–341` (RoutingCase table :59–93, engine round-trip :171–184, live hosted-service routing :190–215); `test/Notifications.Test/PostSendEndpointTests.cs:42–352` (camelCase literals :72–104, commit-separation rule doc :63–69, WebApplicationFactory boot :156–177); ingress `src/Notifications/Controllers/SendController.cs:9–30`.
**Signature:** `private sealed record RoutingCase(string Json, string? ExpectedUserId, string? ExpectedGroup, string? ExpectedAnonymousGroup = null)`; theories `[MemberData(nameof(EngineInputArgs))]` × `[MemberData(nameof(RoutingCaseArgs))]`.
**Data Shape:** TWO dialects of one envelope (`{Type, Payload, ContextId}`): Azure Queue = PascalCase, nulls absent (producer uses `JsonHelpers.IgnoreWritingNull`); `POST /send` = camelCase, explicit nulls (`"reason":null`, `"contextId":null`). Consumer deserializes case-insensitively either way.

### Decisive source
```csharp
// PostSendEndpointTests.cs:63–68 — the deployment-ordering discipline:
/// Do not add a new entry here in the same commit that updates POST /send to handle it.
/// A new entry proves the endpoint accepts the new format, but the point of keeping old
/// entries is to prove the endpoint still accepts the previous format after it has been
/// updated. If both changes land together the old entry is never tested against a
/// Notifications build that lacks the new handling code …
// AzureQueuePipelineTests.cs:26–28 — the round-trip half of the contract:
//   Whatever AzureQueuePushEngine.PushAsync currently produces must be one of those formats,
//   so any wire-format change is caught immediately.
```

**Flow:** each ingestion path gets ONE table of accepted payload literals paired with the exact routing call they must trigger. Direction A replays the REAL producer engines through mock transports and deep-compares (`JsonNode.DeepEquals`) every produced JSON against the table — any producer drift fails CI. Direction B feeds each literal into the real consumer (the actual `AzureQueueHostedService` over a channel-backed fake queue, or the actual app via `NotificationsApplicationFactory` for `/send`) and asserts exactly one `Clients.User/Group` call with the expected name. Both suites document the same migration intent: move routing off inner-payload inspection onto envelope fields so the payload becomes opaque ("dumb proxy") and exhaustive per-type coverage becomes noise.
**Invariant:** (1) producer output must always be a member of the consumer's accepted set — enforced by replay, not by shared types; (2) old entries outlive handler changes by ≥1 release so the previous format keeps CI coverage against builds that already know the new one; (3) adding an entry and teaching the endpoint in the same commit destroys that property — forbidden; (4) dialects differ in case/null policy but share envelope semantics, so tests pin literal strings per path rather than "normalizing".
**Probe:** `PostSendEndpointTests.CapturePayloadAsync` (:239–304) captures what `NotificationsApiPushEngine` actually POSTs by intercepting the mock HTTP body while preserving the real `JsonContent.Create` serialization path, and fakes identity with an unsigned far-future-exp JWT (:344–351) so the token-refresh check passes without signing keys.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "server", query: "RoutingCase SupportedPayloads wire format rolling upgrade", limit: 10 });
```

## Verdict
Adopt: per-ingestion-path RoutingCase tables + producer-replay round-trip assertions + the ≥1-release / separate-commit rules for wire evolution. Adapt: the transport doubles (channel-backed queue client, WebApplicationFactory) to your stack. Omit: Bitwarden's PushType numeric values and specific payload DTOs.
