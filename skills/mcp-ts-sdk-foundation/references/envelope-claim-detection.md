<!-- capsule-v2 -->
# Envelope claim detection — when does a message claim the per-request `_meta` envelope mechanism?

**Source:** typescript-sdk MIT `main@3924de9`; Codebase Memory `mnt-hdd-utopia-inspo-mcp-typescript-sdk`. **Question:** Which inbound messages count as modern-era traffic, and what happens to a present-but-malformed claim?

## Connected graph-selected seam
**Path/Symbol:** `packages/core-internal/src/shared/envelope.ts`: `hasEnvelopeClaim` (:48-51), `envelopeClaimVersion` (:59-63), `requestMetaOf` (:37-41), `carriesValidModernEnvelopeClaim` (inboundClassification.ts :644-654), `validateEnvelopeMeta` delegation (:73-82).
**Signature:** `hasEnvelopeClaim(params: unknown): boolean`; `validateEnvelopeMeta(meta): EnvelopeIssue[]` (delegates to the era codec — the wire layer owns the required-key pre-pass and the wire-exact schema).
**Data Shape:** A claim exists iff the reserved protocol-version key is present in `params._meta`. Other reserved keys (client info, client capabilities, log level), a bare `progressToken`, or unrelated `io.modelcontextprotocol/` keys do NOT constitute a claim on their own.

### Decisive source
```ts
export function hasEnvelopeClaim(params: unknown): boolean {
    const meta = requestMetaOf(params);
    return meta !== undefined && PROTOCOL_VERSION_META_KEY in meta;
}
export function carriesValidModernEnvelopeClaim(params: unknown): boolean {
    if (!hasEnvelopeClaim(params)) return false;
    const claimedVersion = envelopeClaimVersion(params);
    if (claimedVersion === undefined || !isModernProtocolVersion(claimedVersion)) return false;
    const meta = requestMetaOf(params);
    return meta !== undefined && validateEnvelopeMeta(meta).length === 0;
}
```

**Flow:** claim present + names a modern revision + envelope validates ⇒ modern route. Claim present but malformed (bad version string, missing required keys) ⇒ invalid-params rejection naming the offending key(s) — NEVER silent fallback to legacy. No claim ⇒ legacy traffic.

**Invariant:** Detection and validation are deliberately SEPARATE steps: a non-string value under the claim key still counts as a claim (it surfaces as an issue, not as absence). This module never reaches into per-revision wire vocabulary — it maps codec outcomes into ladder shapes, keeping era schemas swappable.

**Probe:** `packages/core-internal/test/shared/inboundClassification.test.ts` (claim/malformed-claim matrix); envelope enforcement order pinned by `packages/core-internal/test/wire/eraGates.test.ts` :244/:256 ("−32601 outranks the missing envelope").

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-mcp-typescript-sdk", query: "hasEnvelopeClaim validateEnvelopeMeta requestMetaOf", limit: 10, fields: ["signature", "name", "file"] });
```

**Verdict:** Adopt narrow key-presence claim detection with loud malformed-claim rejection; adapt the reserved-key set to your envelope schema; omit the two-module re-export dance unless you mirror the layering.
