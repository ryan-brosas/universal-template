<!-- capsule-v2 -->
# Host event payload redactor — how do you persist an arbitrary host payload without leaking secrets or shipping image bytes?

**Source:** pi-fabric (MIT), `feat/veda-runner@4874ac3a`; Codebase Memory `pi-fabric`. **Question:** How is a mesh-published host event payload sanitized, bounded, and made image-safe in ONE serialization pass?

## Host event payload redactor
**Path/Symbol:** `src/actors/host-event-payload.ts:prepareFabricActorHostPayload` (:63–135); helpers `isSensitiveKey` :19–36, `redactInlineSecrets` :38–47, `looksLikeBase64` :49–53.
**Signature:** `prepareFabricActorHostPayload(value: unknown, maxChars: number): {payload, images: ImageContent[], media: {type:"image", mediaIndex, mimeType}[]}`.
**Data Shape:** images = deduped full-fidelity blocks for LLM delivery; media = descriptor stubs persisted in the JSON (`{mediaIndex, mimeType, redacted:true}`); circular objects → sentinel string.

### Decisive source
```ts
const serialized = JSON.stringify(value, (key, nested) => {
    if (key && isSensitiveKey(key)) return "[redacted]";        // KEY-class redaction FIRST
    if (isImageContent(nested)) {
        const sha256 = createHash("sha256").update(nested.mimeType)
            .update("\0").update(nested.data).digest("hex");
        let mediaIndex = imageIndexes.get(sha256);              // content-addressed dedup
        ...
    if (typeof nested === "string") {
        if (looksLikeBase64(nested)) return "[omitted base64]";
        return redactInlineSecrets(nested);
```

**Flow:** one replacer pass over the whole value → sensitive keys nulled by normalized name match (exact OR suffix: apiKey, refreshToken, clientSecret…) → inline secret PATTERNS rewritten (Bearer/Basic tokens, sk-/ghp-/xox- key families, Authorization/Cookie headers, `user:pass@` URLs) → base64 blobs ≥1 KiB replaced by `[omitted base64]` → real images swapped for stubs + hoisted to the images array (sha256(mimeType\0data) keyed) → bigint→string, function/symbol dropped, cycles → `[circular or repeated reference]`.
**Invariant:** Truncation happens on the SERIALIZED json and keeps the TAIL — `json.slice(json.length - maxChars)` — because recency beats validity at the boundary; the tail-slice can cut mid-escape so a re-parse failure degrades the payload to the raw STRING rather than crashing; key-class redaction runs before any pattern pass so even non-string values under sensitive keys are covered; test pins that raw image data and secret VALUES appear NOWHERE in the persisted JSON while Content-Type survives.
**Probe:** `tests/actor-host-event.test.ts` ("extracts and deduplicates images while redacting persisted media and secrets" — two copies of one image → images.length === 1); grep -c 'json.slice(json.length - maxChars)' src/actors/host-event-payload.ts → 1.
**Anchor:** repo root.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-fabric", query: "prepareFabricActorHostPayload redact sensitive images mediaIndex", limit: 10 });
// prepareFabricActorHostPayload Function src/actors/host-event-payload.ts 63-135
```

## Verdict
Adopt the single-replacer-pass ordering (keys → inline patterns → base64 → media hoist) as a reusable persistence sanitizer; adapt the sensitive-key list and token regexes to your threat model; omit the image hoisting if consumers never receive media.
