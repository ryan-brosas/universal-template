<!-- capsule-v2 -->
# Wire-only material lift — how do handlers see the legacy shape while the protocol layer keeps envelope and retry fields?

**Source:** typescript-sdk MIT `main@3924de9`; Codebase Memory `mnt-hdd-utopia-inspo-mcp-typescript-sdk`. **Question:** How do you add wire-level request bookkeeping without breaking every existing handler's view of params?

## Connected graph-selected seam
**Path/Symbol:** `packages/core-internal/src/shared/protocol.ts`: `liftWireOnlyMaterial` (:211-251), `RESERVED_ENVELOPE_META_KEYS` (:186-191), `RETRY_PARAMS_KEYS = ['inputResponses','requestState']` (:199); consumed in `_onrequest` (:933) / `_onnotification` (:874).
**Signature:** `liftWireOnlyMaterial<T extends JSONRPCRequest|JSONRPCNotification>(message: T, kind: 'request'|'notification'): { message: T; lifted: LiftedWireMaterial }`.
**Data Shape:** Lifts (a) reserved `_meta` keys on EVERY message kind, (b) top-level retry params on client-initiated REQUESTS only — notification params keep them untouched (a vendor notification may legitimately use those names). Messages with nothing to lift return UNCHANGED (same reference).

### Decisive source
```ts
const lifted: LiftedWireMaterial = {};
// Surfaced as received; validation/enforcement is the dispatch-time
// classifier's job, not the lift's.
lifted.envelope = envelope as Partial<RequestMetaEnvelope>;
if (Object.keys(nextMeta).length > 0) nextParams._meta = nextMeta;
else delete nextParams._meta;   // a _meta that held only envelope keys disappears entirely
```

**Flow:** raw inbound → lift BEFORE dispatch → handlers (including fallback handler and per-method schema parse) see exactly the 2025-era shape → protocol layer surfaces lifted material via `ctx.mcpReq.envelope` / `.inputResponses` / `.requestState` → era codec validates requiredness at dispatch (`checkInboundEnvelope`), deliberately AFTER the −32601 method-existence gate (method existence outranks parameter validity).

**Invariant:** The universal lift runs ONCE for spec, custom, and fallback paths alike — codecs consume lifted material rather than re-stripping per era. The lift never validates; it only extracts verbatim. Partial envelopes surface as received (`Partial<>`) because a peer on an adjacent revision may legally send a subset.

**Probe:** `packages/core-internal/test/shared/wireOnlyLift.test.ts` :68 ("handler params byte-equal to the 2025 shape"), :139 ("a _meta that holds only envelope keys disappears entirely"), :234 ("2025-era requests pass through untouched — same reference").

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-mcp-typescript-sdk", query: "liftWireOnlyMaterial RESERVED_ENVELOPE_META_KEYS checkInboundEnvelope", limit: 10, fields: ["signature", "name", "file"] });
```

**Verdict:** Adopt lift-before-dispatch to keep handler contracts stable across wire evolution; adapt the reserved-key lists to your envelope; omit the request-vs-notification asymmetry only if your spec reserves retry names on notifications too.
