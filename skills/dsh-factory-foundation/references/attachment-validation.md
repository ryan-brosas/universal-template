<!-- capsule-v2 -->
# Attachment validation — how do user-supplied image data URLs become durable bounded records?

**Source:** dsh-factory MIT `main@3405edc7`; Codebase Memory `mnt-hdd-utopia-inspo-external-ext-dsh-factory`. **Question:** How do I accept pasted images on tasks/comments without trusting client media claims or unbounded payloads?

## attachments()
**Path/Symbol:** `packages/domain/src/mutations.ts` (`attachments`) (:49–60).
**Signature:** `function attachments(inputs: readonly FactoryAttachmentInput[], now: string, maxCount: number, maxBytes: number): FactoryAttachment[]`.
**Data Shape:** allowlist `image/png|jpeg|webp|gif`; name truncated to 160 chars; base64 payload byte-counted AFTER decoding size (`Buffer.byteLength(payload, 'base64')`); defaults 8 attachments / 4_000_000 bytes.

### Decisive source
```ts
if (inputs.length > maxCount) throw new Error(`A Factory task accepts at most ${maxCount} attachments`)
return inputs.map((input) => {
    const match = /^data:([^;,]+);base64,([A-Za-z0-9+/=]+)$/u.exec(input.dataUrl)
    if (match === null || match[1] !== input.mediaType || !['image/png', 'image/jpeg', 'image/webp', 'image/gif'].includes(input.mediaType))
      throw new Error(`Attachment ${JSON.stringify(input.name)} is not a supported matching image data URL`)
    const payload = match[2]
    if (payload === undefined || Buffer.byteLength(payload, 'base64') > maxBytes) throw new Error(`... exceeds ${maxBytes} bytes`)
    return { id: ..., name: input.name.slice(0, 160), ... }
})
```

**Flow:** count gate → per attachment: strict data-URL regex parse (charset-restricted base64) → the URL's OWN media type must EQUAL the declared `mediaType` field AND be in the allowlist → decoded-size cap → durable record with fresh identity. The same validator runs at task creation, session intake, and comment append.
**Invariant:** Media type is verified against the data URL's own header (a client declaring `image/png` while shipping text fails); the regex charset blocks smuggled URLs/characters; validation happens INSIDE the mutation so a bad attachment rejects the whole transaction — no partial persistence.
**Probe:** exercised via domain suite "creates standalone, recurring, finalizer tasks..." path and comment paths; direct deterministic from repo root: `grep -c "not a supported matching image data URL" packages/domain/src/mutations.ts` = 1; `grep -c "accepts at most" packages/domain/src/mutations.ts` = 1.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-external-ext-dsh-factory", query: "FactoryAttachmentInput", limit: 5, fields: ["signature", "name", "file"] });
```
(CLI equivalent verified via sibling name-pattern queries on this project.)

## Verdict
Adopt header-vs-declared matching + strict regex + decode-aware caps inside the transaction. Adapt the allowlist to host supported types.
