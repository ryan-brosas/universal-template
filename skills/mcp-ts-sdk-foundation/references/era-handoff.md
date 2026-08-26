<!-- capsule-v2 -->
# Era-mismatch handoff — what happens when edge-classified traffic lands on an instance of the other era?

**Source:** typescript-sdk MIT `main@3924de9`; Codebase Memory `mnt-hdd-utopia-inspo-mcp-typescript-sdk`. **Question:** When a routing layer sends a classified modern message to a legacy-bound instance (or vice versa), why must the instance refuse rather than adapt?

## Connected graph-selected seam
**Path/Symbol:** `packages/core-internal/src/shared/protocol.ts`: `_onrequest` era-handoff region (:946-983) + drop consult (:947-951); `classifiedWireEra` (`wire/codec.ts` :315-318); `_shouldDropInbound` hook for unclassified traffic.
**Signature:** internal: compares `classifiedWireEra(extra.classification)` against `this._negotiatedWireCodec().era`; on mismatch answers `-32022 Unsupported protocol version`.
**Data Shape:** The typed error carries `{supported: this._supportedProtocolVersions, requested}` where `requested = classification.revision ?? classified-era-label` — the FULL supported list, so the peer can pick a mutually supported version from the error alone.

### Decisive source
```ts
// Era is instance state … Classification is never a per-message era switch —
// it is validated against the instance era below. Hand-wired legacy transports
// never classify, so their behavior is untouched.
if (extra?.classification !== undefined) {
    const classified = classifiedWireEra(extra.classification);
    if (classified !== codec.era) {
        // answer with the typed era error and surface it out of band —
        // never serve the request on a guessed era.
        sendErrorResponse(ProtocolErrorCode.UnsupportedProtocolVersion,
            `Unsupported protocol version: ${requested}`, { supported, requested });
        return;
    }
}
```

**Flow:** entry classifies once at the HTTP boundary → per-request transport carries the classification into dispatch → instance validates classification-era == negotiated-era → mismatch ⇒ typed −32022, handler never runs → match ⇒ registry gate → handler. Unclassified (hand-wired) traffic can additionally be declined by the role class via `_shouldDropInbound`.

**Invariant:** Era is connection state; per-message codec switching from classifications is forbidden by construction (the exact inverse leak the bootstrap-pin design prevents). Serving on a "guessed" era would corrupt every subsequent exchange on that instance — refusal with discovery data is the only safe move. The exact revision wins over the coarse era flag when both are present in the classification.

**Probe:** `packages/core-internal/test/wire/eraGates.test.ts` :379 ("a modern-classified request on a legacy-era instance is an entry/routing error: typed −32022, handler never runs"); drop-hook pinning via `test/shared/protocolDropInboundHook.test.ts`.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-mcp-typescript-sdk", query: "classifiedWireEra _shouldDropInbound MessageClassification", limit: 10, fields: ["signature", "name", "file"] });
```

**Verdict:** Adopt validate-don't-switch semantics at the dispatch boundary; adapt the error payload to your negotiation vocabulary; omit the unclassified-drop hook if all your traffic is always classified.
