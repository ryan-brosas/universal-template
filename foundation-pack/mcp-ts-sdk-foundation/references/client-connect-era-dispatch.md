<!-- capsule-v2 -->
# Client connect era dispatch — how does one `connect()` entry point serve cached-verdict, probed, and plain-legacy handshakes without leaking state across reconnects?

**Source:** typescript-sdk MIT `main@3924de9`; Codebase Memory `typescript-sdk`. **Question:** What are the three connect paths' preconditions, their resume-vs-fresh branches, and the exact ordering of reset → probe → super.connect → handshake?

## Connected graph-selected seam
**Path/Symbol:** `packages/client/src/client/client.ts`: `connect` (:982-995), `_connectPlainLegacy` (:1001-1026), `_legacyHandshake` (:1035-1100), `_connectNegotiated` (:1108-1273), `_connectFromPrior` (:1280-1320), `_resetConnectionState` (:581-616), module-level `validatePrior` (:374-389); probe-window handover in `packages/client/src/client/versionNegotiation.ts`: `ProbeWindow.release` (:316-333), `disarmSpentCloseGuard` (:349-353).
**Signature:** `override async connect(transport: Transport, options?: ConnectOptions): Promise<void>`
**Data Shape:** `ConnectOptions.prior?: PriorDiscovery` (`{kind:'legacy'} | {kind:'modern', discover}`); negotiation plan = `{kind:'legacy'|'auto'|'pin'}`.

### Decisive source
```ts
// :982-995 — the whole dispatch
if (options?.prior != null) {                       // JSON null revives as absent, not a shape error
    return this._connectFromPrior(transport, validatePrior(options.prior), options);
}
const negotiation = resolveVersionNegotiation(this._versionNegotiation, this._supportedProtocolVersionsOption);
if (negotiation.kind !== 'legacy') { return this._connectNegotiated(transport, negotiation, options); }
return this._connectPlainLegacy(transport, options);
// :1146-1163 — cleanup ordering after a failed/successful probe
await transport.close().catch(() => {});  // failed negotiation only
disarmSpentCloseGuard(transport);         // AFTER the cleanup close settles — an armed guard would
                                          // swallow the next GENUINE close on stdio restarts
await super.connect(transport);
// :317-333 ProbeWindow.release() — ONE-SHOT start() pass-through so Protocol's start() is a no-op
transport.start = async function () { if (armed) { armed = false; transport.start = originalStart; return; } return originalStart.call(transport); };
```

**Flow:** prior path validates the blob FIRST (`validatePrior` throws typed
`SdkError(EraNegotiationFailed,'unrecognized prior')` before ANY state change; a legacy verdict
carrying discover-shaped members is corrupt and rejected; modern verdict needs a client-modern ∩
`discover.supportedVersions` overlap or EraNegotiationFailed) → adopt fields + setProtocolVersion,
NO auto-opened listen stream. Negotiated path: resume branch (`sessionId !== undefined`) never
re-probes, just re-pushes the instance-held version; fresh = reset → in-place probe OR disposable-
sibling stdio probe → disarm guard → super.connect → legacy ⇒ shared `_legacyHandshake`, modern ⇒
adopt DiscoverResult + set version + listChanged handlers with configured∩advertised filter +
auto-open listen whose ack wait is bounded by a DERIVED one-shot signal (connect's signal must not
bind the subscription lifetime). Legacy path: fresh connect resets state then runs `_legacyHandshake`
(offers `legacyVersions[0]` only; sets `_negotiatedProtocolVersion` AFTER notifications/initialized;
failure ⇒ `void this.close()` + rethrow).

**Invariant:** every FRESH connect re-negotiates — verdicts are connection state, cleared by
`_resetConnectionState` (which also settles live listen machines with ConnectionClosed, clears
debounce timers, resets the cache while keeping a user-supplied store); an established era is never
demoted by later failures; resume reuses the instance-held version because only the new transport
needs the header pushed.

**Probe:** `packages/client/test/client/versionNegotiation.test.ts` :997-1049 (era scope discipline:
fresh auto connect re-probes; established modern era survives onerror without initialize) and
:966-990 (mid-probe server→client request dropped with zero bytes). `connectPrior.test.ts`
:250-373 (malformed blobs ⇒ typed EraNegotiationFailed before state change; stale body serverInfo
⇒ anonymous identity).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.trace_path({ project: "typescript-sdk", function_name: "typescript-sdk.packages.client.src.client.client.Client.connect", direction: "outbound" });
```

## Verdict
Adopt the three-path dispatch + validate-before-mutate blob hardening for any multi-era client;
adapt the auto-open/listen coupling to hosts without subscriptions; omit the sibling-probe arm
when your transports can always probe in place (see stdio-sibling-probe.md for that machinery,
cached-era-verdicts.md for the PriorDiscovery surface, probe-verdict-classifier.md for the verdict
taxonomy this dispatch consumes).
