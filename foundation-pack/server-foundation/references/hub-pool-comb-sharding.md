<!-- capsule-v2 -->
# Hub pool comb-sharding — how do I route each device registration to one of N notification hubs deterministically, with time-windowed admission?

**Source:** Bitwarden server AGPL-3.0 `main@ac309aa19ed351406a56032d5f26a7a9a99f4abd`; Codebase Memory `server`. **Question:** Which hub owns a given device id, and when does a hub refuse new registrations?

## Comb-sharded pool
**Path/Symbol:** `src/Core/Platform/Push/NotificationHub/NotificationHubPool.cs:8–75` (`FilterInvalidHubs`, `ConnectionFor`); windows in `NotificationHubConnection.cs:107–121` (`RegistrationEnabled`) + 10ms truncation in `From()` :150–162; comb math in `src/Core/Utilities/CoreHelpers.cs:55–86`.
**Signature:** `NotificationHubConnection ConnectionFor(Guid comb)` / `bool RegistrationEnabled(Guid comb)` / `static long BinForComb(Guid combGuid, int binCount)`.
**Data Shape:** pool is built once from settings; invalid hubs (missing name or connection string) are dropped with a warning, never an exception. Device ids are COMB GUIDs — random prefix + timestamp tail — so the id itself carries its creation time.

### Decisive source
```csharp
public bool RegistrationEnabled(DateTime queryTime)
{
    if (queryTime >= RegistrationEndDate || RegistrationStartDate == null)
    {
        return false;
    }
    return RegistrationStartDate < queryTime;
}
```
```csharp
var possibleConnections = _connections.Where(c => c.RegistrationEnabled(comb)).ToArray();
if (possibleConnections.Length == 0)
{
    throw new InvalidOperationException($"No valid notification hubs are available for the given comb ({comb}).\n" +
        $"The comb's datetime is {CoreHelpers.DateFromComb(comb)}." + /* per-hub window dump */);
}
var resolvedConnection = possibleConnections[CoreHelpers.BinForComb(comb, possibleConnections.Length)];
```

**Flow:** config load → drop-and-warn invalid hubs → for a device id: decode its embedded time (`DateFromComb`: days + msec×3.333333 from the GUID tail) → keep connections whose [start, end) window contains it → pick `BinForComb` (HashCodeCombiner fold of the first 10 random bytes % binCount) → that connection's lazy-initialized `HubClient`.
**Invariant:** (1) selection is a pure function of the device id and the configured windows — the same id always lands on the same hub while the fleet is unchanged; (2) `RegistrationStartDate == null` disables registration entirely; end date is exclusive; (3) start dates are truncated to 10ms because comb time granularity (~3.33ms units) cannot represent finer values; (4) zero eligible hubs throws WITH the comb datetime and every hub's window — fail loud with diagnostics.
**Probe:** `test/Core.Test/Platform/Push/NotificationHub/NotificationHubPoolTests.cs:14–99` (warn-on-invalid ×2, throw-on-no-hub) + `NotificationHubConnectionTests.cs:67–205` (full RegistrationEnabled truth table incl. comb-time variants) + `test/Core.Test/Utilities/CoreHelpersTests.cs:53–75` (`DateFromComb` ±4ms round-trip; exact bins e.g. `00000000-0000-0100-…` @500 bins ⇒ bin 19).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "server", query: "NotificationHubPool ConnectionFor RegistrationEnabled BinForComb", limit: 10, fields: ["signature", "lines"] });
```

## Verdict
Adopt: warn-not-throw config filtering; time-window admission keyed off an id-embedded timestamp; deterministic hash-bin assignment so no routing table is needed. Adapt: replace COMB decoding with any monotonic-ish id carrying creation time; replace HashCodeCombiner with your host's stable hash (bins must only be stable within one deployment). Omit: Azure Notification Hubs client construction details and SAS token generation (host-specific).
