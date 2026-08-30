<!-- capsule-v2 -->
# Chat & message external identifiers — What does validation look like for entities that never persist their own DB rows here?

**Source:** Linked Helper v2.130.5 ingest (proprietary — citations-only), pin `?@?`; Codebase Memory `lh-basis` @ 2026-08-23T00:11:49Z. **Question:** how does the guard depth change for lighter-weight identity families?

## Data-only validators, no persistence composition
**Path/Symbol:** `core/public-methods/models/messages/ChatExternalIdentifier/guards.js` — hash validator (9–16), internal validator (17–26), union (27–29); `IChatExternalIdentifier.js:ChatExternalIdentifierTypes` = HASH_ID:'hash-id', INTERNAL_ID:'internal-id'. `core/public-methods/models/messages/MessageExternalIdentifier/guards.js` — single-type validator `isIMessagePublicExternalIdentifierData` (8–15), union `isIMessageExternalIdentifierData` (16–18); `enums.js`: only PUBLIC_ID:'public-id'.
**Signature:** `isIChatExternalIdentifierData(data): boolean`; `isIMessageExternalIdentifierData(data): boolean`.
**Data Shape:** chat hash-id = non-empty string externalId + type tag ONLY (no prefix/length rules — unlike person hashes); chat internal-id adds mirrored `internalId:number`; message = non-empty string externalId + type tag.

### Decisive source
```js
function isIChatInternalExternalIdentifierData(data) {
    const arg = data;
    return (Boolean(arg) &&
        typeof arg.externalId === 'string' &&
        Boolean(arg.externalId) &&
        Boolean(arg.type) &&
        arg.type === ChatExternalIdentifierTypes.INTERNAL_ID &&
        typeof arg.internalId === 'number' &&     // mirrored companion, same rule as org company-id
        !isNaN(arg.internalId));
}
function isIChatExternalIdentifierData(data) {
    return isIChatHashExternalIdentifierData(data) || isIChatInternalExternalIdentifierData(data);
}
// MessageExternalIdentifier — one type, so the "union" degenerates to a direct alias
function isIMessageExternalIdentifierData(data) {
    return isIMessagePublicExternalIdentifierData(data);
}
```

**Flow:** Boolean/truthiness base check -> externalId must be a non-empty string -> type tag must equal the family constant -> optional mirrored numeric companion checked as number. No dbItem, no PAS dates: these validators certify WIRE DATA, not persisted rows.
**Invariant:** validation depth scales with entity persistence depth — person/org identifiers get dbItem+timestamp composites because they are stored; chat/message identifiers stay data-level. A single-type family keeps its union function anyway so callers stay uniform across families.
**Probe:** `node -e` against dist guards: chat `{externalId:'abc', type:'internal-id', internalId:5}` -> true; `internalId:'5'` -> **false**; `{externalId:'ACo...', type:'hash-id'}` -> true WITHOUT any hash-shape check; message `{externalId:'m1', type:'public-id'}` -> true; type:'li-hash-id' -> false.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.get_code_snippet({ project: "lh-basis", qualified_name: "lh-basis.core.public-methods.models.messages.ChatExternalIdentifier.guards.isIChatInternalExternalIdentifierData" });
```

## Verdict
Adopt tiered validation: full composite (dbItem+dates) for persisted identity rows, bare structural guards for transient wire payloads, keeping the union-function CALLING convention identical across tiers. Adapt type tags/mirror fields. Omit person-hash strictness — chat hashes deliberately skip prefix/length rules here. Coverage: no_recorded_issue on all cited files; probes executed against shipped dist modules (no test runner in ingest).
