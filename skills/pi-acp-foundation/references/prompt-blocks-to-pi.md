<!-- capsule-v2 -->
# ACP prompt blocks → pi message — marker-preserving downconvert (no silent context loss)

**Source:** pi-acp-jetbrain MIT `main@27aac05f`; Codebase Memory `pi-acp`. **Question:** When an ACP client sends rich prompt blocks (text, images, resource links, embedded resources, audio), how do you convert to what pi accepts WITHOUT dropping context the user explicitly attached?

## Prompt downconverter
**Path/Symbol:** `src/acp/translate/prompt.ts` whole file (71L): `PiImage` type (:3-7), `promptToPiMessage(blocks): {message, images}` (:9-71).
**Signature:** `promptToPiMessage(blocks: ContentBlock[]): { message: string; images: PiImage[] }`.
**Data Shape:** out `message` is one concatenated string; `images` is `{type:'image', mimeType, data}` with base64 `data` — pi wants raw base64, NO data-url prefix.

### Decisive source
```ts
case 'text':         message += b.text; break
case 'resource_link':
  // lightweight, human-readable hint for the LLM
  message += `\n[Context] ${b.uri}`; break
case 'image':        images.push({ type:'image', mimeType: b.mimeType, data: b.data }); break
case 'resource':
  // Clients should not send this if embeddedContext=false, but be resilient.
  r.text  → `\n[Embedded Context] ${uri} (${mime})\n${r.text}`          // text content inlined
  r.blob  → `\n[Embedded Context] ${uri} (${mime}, ${Buffer.byteLength(r.blob,'base64')} bytes)` // size marker only
  else    → `\n[Embedded Context] ${uri}`
case 'audio':
  // Not supported by pi. Provide a marker so we don't silently drop context.
  message += `\n[Audio] (${b.mimeType}, ${bytes} bytes) not supported by pi-acp-jetbrain`
default: /* ignore unknown block types */
```

**Flow:** single pass over blocks appending into `message` and collecting `images`. Text-bearing payloads are INLINED so the model still sees the content; non-inlinable payloads (binary blobs, audio) degrade to an honest size-tagged marker line instead of vanishing. Unknown future block types are ignored silently (forward-compatible).

**Invariant:** NOTHING the user attached may disappear without a trace — every unsupported/undersupported block becomes a bracketed marker naming type/mime/size (a porter who drops the audio branch makes the model hallucinate that context was understood). Byte length for embedded blobs is computed from BASE64 (`Buffer.byteLength(blob,'base64')`), not the encoded string length.

**Probe:** `test/unit/prompt-to-pi-message.test.ts` — "concatenates text and resource links" (:5), "includes embedded resource text as marker" (:16), "includes embedded resource blob as marker" (:32), "includes audio as marker" (:50, pins the exact string `'\n[Audio] (audio/wav, 3 bytes) not supported by pi-acp-jetbrain'`), "maps image to pi image content" (:59).
**Coverage:** check_index_coverage `no_recorded_issue` + `metadata_match`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-acp", query: "promptToPiMessage resource_link Embedded Context audio", limit: 6, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the marker-per-block doctrine (inline what you can, honestly label what you can't) and the base64 byte accounting. Adapt marker wording/format to your host. Omit nothing.
