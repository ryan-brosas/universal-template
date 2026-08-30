<!-- capsule-v2 -->
# Outbound bootstrap pins — which codec serves a message sent BEFORE any version is negotiated?

**Source:** typescript-sdk MIT `main@3924de9`; Codebase Memory `mnt-hdd-utopia-inspo-mcp-typescript-sdk`. **Question:** During the chicken-and-egg window (negotiated version still unset), how do lifecycle messages pick an era without leaking one era's methods onto the other?

## Connected graph-selected seam
**Path/Symbol:** `packages/core-internal/src/wire/bootstrap.ts`: `bootstrapOutboundCodec` (:30-45) incl. scope-notes docblock (:1-26); consumed by `packages/core-internal/src/shared/protocol.ts`: `_resolveOutboundCodec` (:1312-1318).
**Signature:** `bootstrapOutboundCodec(method: string): WireCodec | undefined` — consulted ONLY while `_negotiatedProtocolVersion === undefined`.
**Data Shape:** `initialize`/`notifications/initialized` → legacy codec by definition (initialize IS the legacy handshake); `server/discover` → modern codec (exists only on 2026 era); anything else → `undefined` ⇒ falls back to the instance's negotiated codec (legacy default).

### Decisive source
```ts
// `ping` is deliberately NOT pinned. A bare {method:'ping'} carries no era
// marker, and pinning it would let a negotiated-modern session emit a
// 2025-only method onto the modern leg (the exact inverse leak registry
// membership exists to prevent).
case 'server/discover': {
    // The modern discovery exchange, 2026-era only.
    return codecForVersion(MODERN_WIRE_REVISION);
}
default: {
    return undefined;
}
```

**Flow:** send → `_resolveOutboundCodec(method)` → if negotiated version unset, try bootstrap pin → else (and after negotiation always) resolve from instance state → `_assertOutboundRequestInEra` kills spec-methods foreign to the resolved era locally with typed `MethodNotSupportedByProtocolVersion`.

**Invariant:** Pins are OUTBOUND-ONLY and apply only pre-negotiation; once a version exists the instance era is authoritative and a negotiated session NEVER re-routes a method onto the other era. Inbound truth is always the instance's negotiated era — an edge classification is validated against it, never used as a per-message codec switch. `ping` stays unpinned so era-gating (present on 2025, absent from 2026) applies uniformly.

**Probe:** `packages/core-internal/test/wire/eraGates.test.ts` :150 ("ping on a modern-era instance is −32601 by absence"); :137 ("a legacy-era instance … era is fixed per instance").

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-mcp-typescript-sdk", query: "bootstrapOutboundCodec _resolveOutboundCodec", limit: 10, fields: ["signature", "name", "file"] });
```

**Verdict:** Adopt method-keyed bootstrap pins over a global "pre-negotiation = legacy" rule (it would misroute server/discover); adapt pin table to your handshake methods; omit the docblock's spec-history rationale once your pins are test-pinned.
