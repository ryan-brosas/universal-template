<!-- capsule-v2 -->
# recording-pipeline-selection — How do you pick the browser recording pipeline (streaming vs buffered) and codec labels from what the platform ACTUALLY supports?

**Source:** cap AGPL-3.0 `main@0ce9e67516b14449c4263c0b173c85c40f30421b`; Codebase Memory `ext-cap`. **Question:** What decides streaming-webm vs buffered-raw, and why are codec metadata labels derived from the negotiated mime type instead of assumed vp9/opus?

## Chromium-only prefers streaming webm; audio presence REORDERS candidate lists; codec labels parsed from `codecs="..."`, never assumed
**Path/Symbol:** `packages/recorder-core/src/recorder-utils.ts:98-123` (`shouldPreferStreamingUpload`), `:133-183` (`selectRecordingPipelineFromSupport`), `:223-253` (`describeRecordingCodecs`).
**Signature:** `selectRecordingPipelineFromSupport(hasAudio: boolean, isMimeSupported: (candidate: string) => boolean, options?: {preferStreamingUpload?: boolean}): RecordingPipeline | null`.
**Data Shape:** `RecordingPipeline = { mode:"streaming-webm", supportsProgressiveUpload:true } | { mode:"buffered-raw", supportsProgressiveUpload:false }`; iPad/iPhone/iPod and Firefox and pure-Safari force buffered.

### Decisive source
```ts
const webmCandidates = hasAudio
    ? [...WEBM_MIME_TYPES.withAudio, ...WEBM_MIME_TYPES.videoOnly]
    : [...WEBM_MIME_TYPES.videoOnly, ...WEBM_MIME_TYPES.withAudio];
...
// Derive the codec labels that get attached to the upload as object metadata
// from the codecs the recorder actually negotiated, rather than assuming vp9 /
// opus for every webm container. A platform that only encodes vp8 (some
// Chromebooks) would otherwise be mislabelled, and an mp4 fallback carries aac,
// not opus.
```

**Flow:** Browser sniff uses userAgentData brands when available (Chromium family ⇒ streaming preference). Candidate ordering flips on hasAudio so the first SUPPORTED mime matches the actual stream shape. Fallback chain: supported-webm+streaming → supported-mp4/webm buffered → supported-webm buffered → null. Codec derivation parses the `codecs=` parameter; unknown prefixes fall back per-container (webm⇒vp8/opus, mp4⇒h264/aac).
**Invariant:** The negotiated mime string is ground truth for BOTH container and codec claims — labeling a vp8 Chromebook recording as vp9 breaks downstream transcode decisions. Audio-first ordering must mirror the real track layout or the recorder negotiates a mime it can't encode into.
**Probe:** deterministic pins: `grep -n 'describeRecordingCodecs' packages/recorder-core/src/recorder-utils.ts` (:223); package-boundary test suite `packages/recorder-core/__tests__/package-boundaries.test.ts` guards module coupling.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-cap", query: "selectRecordingPipeline shouldPreferStreamingUpload describeRecordingCodecs", limit: 10 });
```

## Verdict
Adopt capability-driven selection + derived codec metadata. Adapt mime tables to your supported containers.
