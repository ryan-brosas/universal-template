<!-- capsule-v2 -->
# Hash-pinned video pipeline init/review/export gates — how do you turn an agent's recording into a VERIFIED MP4 without trusting stale artifacts?

**Source:** browser-harness MIT `main@41108b8676d4bdb58b26ab3b079c0b7b0f8f3926`; Codebase Memory `browser-harness`. **Question:** What integrity checks stand between edit-brief authoring and final export?

## source-manifest → review hashes → composition equality
**Path/Symbol:** `src/browser_harness/video.py:write_source_manifest/verify_source_manifest/file_hash` (:110-173) + `src/browser_harness/video_render.py:compile_recording/export` (:45-54, :413-449).
**Signature:** `write_source_manifest(recording)` sha256s {events.jsonl, meta.json, recording-summary.json} ∪ numeric-stem frames into `video-source.json`; `export(recording, output, reviewed)` requires `--reviewed`.
**Data Shape:** REVIEW_ARTIFACTS = {composition.js, recording-summary.json, edit-brief.json, video-source.json, video.html}; renderer-review.json carries artifactHashes; export refuses existing output/webm/.crdownload; final MP4 duration must match composition within max(1s, 8%) plus `-err_detect explode` full decode.

### Decisive source
```python
video.verify_source_manifest(recording)          # sources unchanged since init
comp = load_composition(recording)
expected_comp = compile_recording(recording, write=False)
if comp != expected_comp:
    raise RuntimeError("composition.js is not the current compiled brief; rerun review")
...
for name, expected_hash in artifact_hashes.items():
    path = recording / name
    if not path.is_file() or video.file_hash(path) != expected_hash:
        raise RuntimeError(f"{name} changed after review; rerun it")
renderer = recording / "video.html"
if video.file_hash(renderer) != video.file_hash(TEMPLATE):
    raise RuntimeError("renderer is not the current shared template; rerun review")
```

**Flow:** init copies template + writes sanitized summary + source manifest → review compiles (manifest-verified), renders beats headlessly, writes contact sheet + report WITH artifact hashes → export demands --reviewed flag, zero report errors, byte-equal recomputed composition, hash-equal artifacts, hash-equal renderer template, .mp4 suffix, no clobbering → CDP-driven webm capture → ffmpeg libx264 convert → ffprobe duration verification.
**Invariant:** ANY input change after its gate invalidates downstream artifacts — human review certifies exactly the bytes that ship; obsolete review files are deleted up front so stale evidence can't satisfy new runs; refusing to overwrite makes every export reproducible-from-evidence.
**Probe:** No direct unit tests for video.py/video_render.py — coverage caveat (deterministic pure-validation surface; anchors verified in source). Compile-side validation contract captured separately in video-brief-validation.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "browser-harness", query: "source manifest verify export review", limit: 10, fields: ["signature", "file"] });
```

## Verdict
Adopt manifest→review→recompute-equality gating for any generated-media or compiled-artifact pipeline. Adapt artifact sets. Keep duration-tolerance verification even if your renderer differs.
