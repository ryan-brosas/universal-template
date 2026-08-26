<!-- capsule-v2 -->
# File part data normalization — how do legacy untagged file parts and four tagged shapes collapse into one v4 provider shape without misclassifying a data URL?

**Source:** Vercel AI SDK Apache-2.0 `main@d25cae2722bfaed94c56d992c6df399a736db7a9`; Codebase Memory `ai`. **Question:** What is the total conversion order for `FilePart.data` (string | URL | Uint8Array | ArrayBuffer | Buffer | tagged object), and which input must throw rather than convert?

## convertToLanguageModelV4FilePart
**Path/Symbol:** `packages/ai/src/prompt/file-part-data.ts:convertToLanguageModelV4FilePart` (:73-125); helpers `convertUrlToFilePartData` (:27-42), `convertInlineDataToFilePartData` (:44-64), `isTaggedFileData` (:14-20).
**Signature:** `(content: FilePart['data']): {data: LanguageModelV4FilePart['data'], mediaType: string | undefined}`.
**Data Shape:** Output data is exactly one of `{type:'data', data: base64-string|Uint8Array}`, `{type:'url', url}`, `{type:'reference', reference}`, `{type:'text', text}`; `mediaType` is extracted ONLY from a `data:` URL, else undefined.

### Decisive source
```ts
if (isTaggedFileData(content)) {
  switch (content.type) {
    case 'data':
      if (typeof content.data === 'string' && content.data.startsWith('data:')) {
        throw new InvalidDataContentError({ content: content.data,
          message: 'Data URLs are not valid inline data. Pass them as { type: "url", url } instead.' });
      }
      return convertInlineDataToFilePartData(content.data);
    case 'url':    return convertUrlToFilePartData(content.url);
    case 'reference': return { data: { type: 'reference', reference: content.reference }, mediaType: undefined };
    case 'text':   return { data: { type: 'text', text: content.text }, mediaType: undefined };
  }
}
if (content instanceof URL) return convertUrlToFilePartData(content);
if (typeof content === 'string') {
  try { return convertUrlToFilePartData(new URL(content)); }   // parseable string = URL
  catch { return convertInlineDataToFilePartData(content); }   // else = base64/inline
}
if (isProviderReference(content)) return { data: { type: 'reference', ... } };
return convertInlineDataToFilePartData(content as DataContent);
```

**Flow:** tagged check first → per-type branch → legacy ladder: URL instance → parseable-URL string (try/catch IS the classifier) → provider reference → inline fallback. `convertUrlToFilePartData` splits `data:` URLs via `splitDataUrl` and THROWS `InvalidDataContentError` when mediaType or base64 half is missing; `convertInlineDataToFilePartData` maps ArrayBuffer/Buffer→`new Uint8Array(...)`, strings pass as base64 untouched.
**Invariant:** A `data:` URL is NEVER valid inline data — the explicit startsWith('data:') throw exists because silently base64-encoding the whole URL string produces corrupt assets downstream; the same rule makes the try/catch order load-bearing (`new URL('data:...')` parses fine, so plain strings that LOOK like URLs must be checked before inline fallback). Binary inputs are normalized to Uint8Array at this boundary so providers never see Buffer/ArrayBuffer variants.
**Probe:** `packages/ai/src/prompt/file-part-data.test.ts:98` ("rejects { type: \"data\", data: data URL string }"), `:32/:43` (URL string vs URL instance), `:24/:91` (base64 string not treated as URL), `:51/:115` (data-URL mediaType extraction through both entry shapes), `:6/:14` (binary wrapping).

## Get live surrounding code
**Retrieve:**
```bash
echo '{"project":"ai","query":"convertToLanguageModelV4FilePart splitDataUrl InvalidDataContentError isProviderReference","limit":5}' | codebase-memory-mcp cli search_graph
```

## Verdict
Adopt the full decision ladder including the data-URL-inline rejection and the try/catch URL classifier; adapt the binary input set (drop Buffer if your host lacks Node buffers) but keep the Uint8Array output guarantee; omit the `reference` branch only if your provider layer has no provider-reference concept. All branches direct-test-pinned at this HEAD.
