<!-- capsule-v2 -->
# Thumbnail memory bomb guard — how do you resize untrusted images on a <1 GB worker without letting one decompression bomb OOM-loop the job queue?

**Source:** nocodb (Sustainable Use License, develop branch) `develop@f7513664f3f3`; Codebase Memory project `nocodb`. **Question:** How are input pixel caps chosen per codec, and why is metadata checked before decode?

## format-aware limitInputPixels ladder
**Path/Symbol:** `packages/nocodb/src/modules/jobs/jobs/thumbnail-generator/generators/base-thumbnail-generator.ts:BaseThumbnailGenerator.generateThumbnails` (42-153); caps at 23-29.
**Signature:** `generateThumbnails(file: Buffer, relativePath: string, storageAdapter): Promise<{card_cover, small, tiny} | null>`; `MAX_INPUT_PIXELS_SHRINKABLE = 100e6` (jpeg/jpg/webp), `MAX_INPUT_PIXELS_FULL_DECODE = 24e6` (everything else), both env-overridable.
**Data Shape:** outputs `nc/thumbnails/<relativePath>/{card_cover(512), small(128), tiny(64)}.jpg`, quality 80, lanczos3 cover-fit.

### Decisive source
```ts
const SHRINK_ON_LOAD_FORMATS = new Set(['jpeg', 'jpg', 'webp']);
// JPEG/WEBP support shrink-on-load → libvips decodes at reduced scale when
// resizing down; peak stays small. Everything else fully decodes to pixels*channels.
let metadata;
try { metadata = await sharp(thumbnailBuffer, { limitInputPixels: false }).metadata(); }
catch (e) { return null; }                       // unreadable header → skip gracefully
const maxInputPixels = SHRINK_ON_LOAD_FORMATS.has(metadata.format)
  ? MAX_INPUT_PIXELS_SHRINKABLE : MAX_INPUT_PIXELS_FULL_DECODE;
if (inputPixels > maxInputPixels) return null;   // reject BEFORE allocating raster
const sharpImage = sharp(thumbnailBuffer, { limitInputPixels: maxInputPixels }); // backstop
```

**Flow:** parse header cheaply (`metadata()` reads only the header) → compute width×height → compare against the format's cap → only then create the decoding pipeline. Per size, `sharpImage.clone()` gives an independent pipeline snapshot so rotate/resize don't mutate shared state.
**Invariant:** two layers — the pre-decode cap decides skip-vs-go; the finite `limitInputPixels` on the real pipeline backstops lying headers. `.rotate()` with no args bakes EXIF orientation in but must be called ONLY for orientation ≠ 1, or shrink-on-load silently disables for the common case. A failed thumbnail returns `null`, never throws — one bad attachment must not fail the whole job batch.
**Probe:** no unit test upstream. Source-grounded probe: `base-thumbnail-generator.ts:64-96` — metadata-then-cap-then-finite-limit sequence with the crash-loop comment at :8-11; `:106-108` + `:127-129` — conditional rotate and clone-per-size.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "BaseThumbnailGenerator generateThumbnails limitInputPixels sharp", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt format-aware pixel caps, header-first validation, clone-per-output pipelines, and null-not-throw failure; adapt cap values/env names and size ladder to host; omit sharp wiring via Noco singleton. Coverage caveat: no in-repo tests; source-grounded.
