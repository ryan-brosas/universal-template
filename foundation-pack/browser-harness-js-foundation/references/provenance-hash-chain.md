<!-- capsule-v2 -->
# Hash-sealed provenance chain — how does the exporter PROVE no source frame or review artifact changed since a human looked?

**Source:** browser-harness-js MIT `main@6b189406`; Codebase Memory `browser-harness-js`. **Question:** What is the exact hash/seal ladder from raw recording to exported MP4?

## video-source.json → renderer-review.json + .sha256 seal → export re-verifies EVERYTHING
**Path/Symbol:** `skills/cdp/sdk/video.ts:writeSourceManifest` (:121-133), `verifySourceManifest` (:135-155); `video-render.ts:artifactHashes` (:389-391), `review` seal write (:461-463), `verifyReviewArtifacts` (:491-504), `exportVideo` gate ladder (:556-583).
**Signature:** `verifySourceManifest(recording): Json` (throws `BriefError`) · export-side checks are inline in `exportVideo`.
**Data Shape:** source manifest = `{recording, started, explicit, files: {basename: sha256}}` over events.jsonl + meta.json + recording-summary.json (if present) + every `\d+.jpg`; REVIEW_ARTIFACTS = composition.js, recording-summary.json, edit-brief.json, video-source.json, video.html.

### Decisive source
```ts
if (JSON.stringify(names) !== JSON.stringify(expected)) {
  throw new BriefError('recording source files changed after initialization');   // set equality, not subset
}
for (const path of paths) {
  if (manifest.files[basename(path)] !== fileHash(path)) {
    throw new BriefError(`recording source changed after initialization: ${basename(path)}`);
  }
}
...
// exportVideo:
const expectedComposition = compileRecording(recording, false);
if (JSON.stringify(composition) !== JSON.stringify(expectedComposition)) {
  throw new Error('composition.js is not the current compiled brief; rerun review');
}
if (fileHash(join(recording, 'video.html')) !== fileHash(TEMPLATE)) throw new Error('renderer is not the current shared template; rerun review');
```
plus the self-seal: `renderer-review.sha256 = fileHash(renderer-review.json)`, re-checked before export (`readFileSync(sealPath).trim() !== fileHash(reviewPath)` ⇒ "changed after review; rerun it").

**Flow:** `init` hashes all evidence into video-source.json (explicit flag from meta.auto) → author edits brief → `review` re-verifies sources, compiles, renders, then writes artifact hashes for ALL five artifacts + every review image INTO renderer-review.json and seals that file's own hash → `export --reviewed` re-walks the whole chain: seal match → zero errors in report → source manifest → composition byte-equality against a fresh compile → template identity → per-artifact hash match → per-review-image hash with escape check.
**Invariant:** (1) ANY mutation — brief, frame, composition, even the shared HTML template — invalidates the seal; there is no partial re-verification. (2) The manifest check is SET equality (added OR removed files both fail), then per-file hash. (3) The review report hashes itself — tampering with the report breaks its own seal. (4) Composition is verified by RE-COMPILING rather than trusting the stored file.
**Probe:** direct test `skills/cdp/sdk/video.test.ts`: `'recording initialization hides typing and hashes exact evidence'` tampers `0002.jpg` and asserts `/source changed/` (:63-64).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "browser-harness-js", query: "verifySourceManifest", limit: 3, fields: ["signature", "name", "file"] });
// resolves video.verifySourceManifest @ video.ts:135-155
```

## Verdict
Adopt the full-chain seal whenever an automated artifact claims human review; adapt which artifacts join REVIEW_ARTIFACTS to your pipeline; omit nothing between init and export — a single unverified hop turns the provenance claim into decoration.
