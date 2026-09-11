<!-- capsule-v2 -->
# Beacon content-type verdict — how do you record a fire-and-forget sendBeacon whose only outcome signal is a boolean?

**Source:** OpenReplay AGPL-3.0 `main@99eb60032f70906f6887195c400f173c00a08522`; Codebase Memory `openreplay`. **Question:** What can a recorder honestly report about `navigator.sendBeacon`, which returns synchronously and never exposes response headers or status?

## Class-derived Content-Type + boolean verdict
**Path/Symbol:** `networkProxy/src/beaconProxy.ts:getContentType` (:6-17), `BeaconProxyHandler.apply` (:28-73), `BeaconProxy.create` (:77-98).
**Signature:** `getContentType(data?: BodyInit): string`; `apply(target, thisArg, argsList): boolean`.
**Data Shape:** requestType 'beacon'; method forced 'POST'; Content-Type derived purely from the BodyInit class: `Blob.type` / `multipart/form-data` / `application/x-www-form-urlencoded;charset=UTF-8` (URLSearchParams) / default `text/plain;charset=UTF-8`.

### Decisive source
```ts
const isSuccess = target.apply(thisArg, argsList)
if (isSuccess) {
  item.status = 0
  item.statusText = 'Sent'
  item.readyState = 4
} else {
  item.status = 500
  item.statusText = 'Unknown'
}
const msg = item.getMessage(); if (msg) this.sendMessage(msg)
return isSuccess
```

**Flow:** service-URL? pass through untouched : build NetworkMessage (url, pathname+search name, GET data from searchParams, body via genStringBody) → call through → map the boolean to a terminal record ('Sent'/readyState 4 vs 500/'Unknown') → emit one message → return the original boolean unchanged.
**Invariant:** The app's return value must pass through unmodified, and the recorded status must never claim an HTTP code that was never observed — success is `0/'Sent'`, not 200; failure is synthetic `500/'Unknown'`. Timing is a single synchronous window (startTime→endTime around the call).
**Probe:** no dedicated upstream test file covers beaconProxy at pin (recorded coverage caveat). Deterministic anchors: `grep -c statusText networkProxy/src/beaconProxy.ts` → `3` ('Pending'/'Sent'/'Unknown'); `grep -c "'Sent'" networkProxy/src/beaconProxy.ts` → `1`.
**Coverage:** beaconProxy.ts `no_recorded_issue`/`metadata_match` @ gen 2026-08-25T20:08:30Z.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openreplay", query: "sendBeacon beacon proxy content type BodyInit sent pending status", limit: 10 });
```
(Executed at pin: top hits BeaconProxy/BeaconProxyHandler/getContentType in beaconProxy.ts.)

## Verdict
Adopt the honest-verdict mapping and class-derived Content-Type for any beacon/ping instrumentation. Adapt statusText vocabulary to your player's taxonomy. Omit duration if your beacons are truly synchronous no-ops.
