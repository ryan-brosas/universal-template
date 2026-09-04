<!-- capsule-v2 -->
# Gzip-magic fallback decryption — how do you decrypt payloads that may or may not be compressed?

**Source:** aliasvault AGPL-3.0 (patterns-only) `main@95903e926f757046ef32feb7ca147900de0a6802`; Codebase Memory `ext-aliasvault`. **Question:** How does a client read `messageSource` from both pre-v0.31 (plain) and v0.31+ (gzip-then-encrypt) APIs without a version flag?

## Magic-byte sniff after decryption
**Path/Symbol:** `apps/browser-extension/src/utils/EncryptionUtility.ts:158-188` (`symmetricDecryptMaybeCompressed`, `decodeMaybeGzipped`), call site :374-377.
**Signature:** `async symmetricDecryptMaybeCompressed(base64Ciphertext: string, base64Key: string): Promise<string>`; private `decodeMaybeGzipped(bytes: Uint8Array): Promise<string>`.
**Data Shape:** Order of operations is ENCRYPT-AFTER-COMPRESS, so the client must DECRYPT FIRST then sniff: gzip magic = bytes[0]==0x1f && bytes[1]==0x8b.

### Decisive source
```ts
// Gzip magic number (0x1f 0x8b); anything else is treated as plain UTF-8.
if (bytes.length < 2 || bytes[0] !== 0x1f || bytes[1] !== 0x8b) {
  return decoder.decode(bytes);
}
if (typeof DecompressionStream === 'undefined') {
  throw new Error('Gzip decompression is not supported by this browser');
}
const stream = new Blob([bytes as BlobPart]).stream().pipeThrough(new DecompressionStream('gzip'));
const decompressed = await new Response(stream).arrayBuffer();
return decoder.decode(decompressed);
```

**Flow:** AES-GCM decrypt to raw bytes → sniff first two bytes → non-gzip ⇒ UTF-8 decode directly → gzip ⇒ DecompressionStream pipe → UTF-8 decode. Used ONLY for `messageSource` today (:374-377); other fields stay plain-decrypted.
**Invariants:** (1) Compression happens BEFORE encryption — ciphertext hides the magic bytes, so sniffing must occur post-decrypt. (2) The check is length-guarded (`length < 2`) and treats ANY error-free non-magic payload as valid UTF-8 — never throw on legacy data. (3) Missing DecompressionStream support is an explicit runtime error, not silent garbage. (4) Newer fields can adopt the wrapper independently; old clients simply can't be served gzip by the server until they upgrade (server-side version gate).
**Probe:** `grep -c 'bytes\[1\] !== 0x8b' apps/browser-extension/src/utils/EncryptionUtility.ts` → `1`; `grep -c 'DecompressionStream' apps/browser-extension/src/utils/EncryptionUtility.ts` → `2`.

## Direct tests
**Path/Symbol:** `apps/browser-extension/src/utils/__tests__/EncryptionUtility.crypto.test.ts:237-295` — "decrypts an uncompressed message source" (:267) and "gunzips a compressed message source" (:281).
**Probe:** run jest where node_modules exists; deterministic probes above executed at pin `95903e92`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-aliasvault", query: "decodeMaybeGzipped", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt decrypt-then-sniff with magic-byte gating for transparent codec migration; adapt compression codec; omit Blob/streams browser specifics. Upstream jest coverage exists but was not executed here.
