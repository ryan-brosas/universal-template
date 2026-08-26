<!-- capsule-v2 -->
# Data-content codec — when does a string mean base64 versus raw bytes, and how do binary variants normalize?

**Source:** Vercel AI SDK Apache-2.0 `main@d25cae2722bfaed94c56d992c6df399a736db7a9`; Codebase Memory `ai`. **Question:** What conversions does `DataContent` (base64 string | Uint8Array | ArrayBuffer) undergo, and which failures become typed errors versus silent pass-through?

## convertDataContentToBase64String / convertDataContentToUint8Array
**Path/Symbol:** `packages/ai/src/prompt/data-content.ts:convertDataContentToBase64String` (:14-24), `convertDataContentToUint8Array` (:32-57); URL splitter `split-data-url.ts:splitDataUrl` (:1-17).
**Signature:** `convertDataContentToBase64String(content: DataContent): string`; `convertDataContentToUint8Array(content: DataContent): Uint8Array`; `splitDataUrl(dataUrl: string): {mediaType: string | undefined, base64Content: string | undefined}`.
**Data Shape:** Strings are ASSUMED base64 (never decoded as UTF-8); ArrayBuffer wraps via `new Uint8Array(...)`; anything else reaching the tail of the to-Uint8Array ladder throws `InvalidDataContentError`.

### Decisive source
```ts
// to Uint8Array:
if (content instanceof Uint8Array) {
    return content;
  }
  if (typeof content === 'string') {
    try { return convertBase64ToUint8Array(content); }
  catch (error) {
    throw new InvalidDataContentError({
      message: 'Invalid data content. Content string is not a base64-encoded media.',
      content, cause: error,
    });
  }
}
if (content instanceof ArrayBuffer) return new Uint8Array(content);
throw new InvalidDataContentError({ content });
```
```ts
// splitDataUrl never throws — malformed input yields {undefined, undefined}:
try {
  const [header, base64Content] = dataUrl.split(',');
  return { mediaType: header.split(';')[0].split(':')[1], base64Content };
} catch { return { mediaType: undefined, base64Content: undefined }; }
```

**Flow:** identity for Uint8Array → string = strict base64 decode with typed wrap → ArrayBuffer view. The base64 decode failure is deliberately re-thrown as `InvalidDataContentError` so upstream prompt conversion reports a domain error, not an opaque atob crash.
**Invariant:** String content is ALWAYS interpreted as base64 in this layer — treating it as UTF-8 text silently corrupts binary assets; the to-string direction passes strings through UNCHANGED (already base64). `splitDataUrl` is the non-throwing counterpart: its `{undefined, undefined}` result is what makes `file-part-data.ts` throw `InvalidDataContentError` at the call site instead (error responsibility lives with the caller).
**Probe:** `packages/ai/src/prompt/file-part-data.test.ts:51/:115` (data-URL split feeding mediaType extraction); `packages/provider-utils/src/detect-media-type.test.ts` (base64 vs byte parity on every signature — same assumption). Direct unit file for data-content.ts itself: none at this pin (coverage caveat; behavior pinned through consumers).

## Get live surrounding code
**Retrieve:**
```bash
echo '{"project":"ai","query":"convertBase64ToUint8Array InvalidDataContentError splitDataUrl DataContent","limit":5}' | codebase-memory-mcp cli search_graph
```

## Verdict
Adopt "string means base64" + typed error wrapping + non-throwing split helper; adapt error type names to your domain hierarchy but keep single-flavor classification; omit the ArrayBuffer branch only in runtimes without TypedArray views. Coverage caveat recorded: no dedicated direct test for this file; verified via consumer suites and parity tests.
