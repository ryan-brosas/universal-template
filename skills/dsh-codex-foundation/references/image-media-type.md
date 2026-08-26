<!-- capsule-v2 -->
# Image media classifier — trust magic bytes, not names

**Source:** dsh-codex Apache-2.0 main@e3e54e206f7c829503c7e6eed378643ba0416792; Codebase Memory dsh-codex. **Question:** how should image inputs be classified consistently for both generation references and read_image without trusting file extensions or remote metadata?

## imageMediaType
**Path/Symbol:** src/read-image-enhancement.ts:54-66 imageMediaType.
**Signature:** imageMediaType(data: Uint8Array): ImageMediaType | undefined.
**Data Shape:** The classifier accepts raw bytes and returns exactly image/png, image/jpeg, image/gif, image/webp, or undefined. It has no filesystem, URL, or attachment side effects, so both imagegen and read_image can share it.

### Decisive source
~~~ts
if (data.length >= 8 && data[0] === 0x89 && data[1] === 0x50 && data[2] === 0x4e && data[3] === 0x47
  && data[4] === 0x0d && data[5] === 0x0a && data[6] === 0x1a && data[7] === 0x0a) return 'image/png'
if (data.length >= 3 && data[0] === 0xff && data[1] === 0xd8 && data[2] === 0xff) return 'image/jpeg'
if (data.length >= 6) {
  const signature = String.fromCharCode(...data.subarray(0, 6))
  if (signature === 'GIF87a' || signature === 'GIF89a') return 'image/gif'
}
if (data.length >= 12
  && String.fromCharCode(...data.subarray(0, 4)) === 'RIFF'
  && String.fromCharCode(...data.subarray(8, 12)) === 'WEBP') return 'image/webp'
return undefined
~~~

**Flow:** check length before each signature read, match PNG/JPEG/GIF/WebP headers, and return undefined for every other or too-short byte sequence.
**Invariant:** content classification is independent of extension, path, URL, or caller claims; unsupported bytes cannot reach attachment saving or provider requests, and the same classifier governs input references and generated-output PNG validation.
**Probe:** tests/read-image-enhancement.spec.ts:152-165 downloads PNG bytes and returns an image; tests/imagegen.spec.ts:165-180 sends PNG reference bytes and 117-150 validates the generated PNG path. The full direct suite passed; there is no dedicated JPEG/GIF/WebP unit test, so those branches remain source-confirmed.

## Get live surrounding code
**Retrieve:**
~~~ts
await mcp.codebase_memory.search_graph({ project: 'dsh-codex', qn_pattern: 'dsh-codex\\.src\\.read-image-enhancement\\.imageMediaType', limit: 10, fields: ['signature', 'name', 'file', 'lines'] });
~~~

## Verdict
Adopt a small side-effect-free magic-byte classifier and make downstream attachment/provider code consume its result. Adapt the supported media enum and signature table; retain rejection by default. Omit extension-only or content-type-only acceptance. Coverage is no_recorded_issue + metadata_match; direct tests exercise the PNG branch and unsupported downstream rejection, while non-PNG signatures lack dedicated direct tests.
