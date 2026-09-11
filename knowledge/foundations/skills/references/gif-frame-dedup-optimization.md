<!-- capsule-v2 -->
# GIF frame dedup & size-optimization — how do you shrink an animated GIF without silently changing its timing?

**Source:** anthropics/skills Apache-2.0 `main@3b3fad96af16`; Codebase Memory `skills`. **Question:** How are near-duplicate frames detected and removed, and what does removal do to animation duration?

## Chained-anchor similarity filter + uncompensated uniform duration
**Path/Symbol:** `skills/slack-gif-creator/core/gif_builder.py`:`GIFBuilder.deduplicate_frames` (:124–158), `add_frame` (:34–52), `save` (:160–265).
**Signature:** `def deduplicate_frames(self, threshold: float = 0.9995) -> int`; `def save(self, output_path, num_colors=128, optimize_for_emoji=False, remove_duplicates=False) -> dict`.
**Data Shape:** frames = list of RGB numpy arrays; similarity = `1 - mean(|prev_kept − curr|)/255`; returns count removed; save() returns info {path,size_kb,size_mb,dimensions,frame_count,fps,duration_seconds,colors}.

### Decisive source
```python
deduplicated = [self.frames[0]]
for i in range(1, len(self.frames)):
    prev_frame = np.array(deduplicated[-1], dtype=np.float32)   # last KEPT frame
    curr_frame = np.array(self.frames[i], dtype=np.float32)
    diff = np.abs(prev_frame - curr_frame)
    similarity = 1.0 - (np.mean(diff) / 255.0)
    if similarity < threshold:
        deduplicated.append(self.frames[i])
    else:
        removed_count += 1
```
And the timing trap downstream in `save()`:
```python
frame_duration = 1000 / self.fps          # UNIFORM duration, applied AFTER any removal
imageio.imwrite(output_path, optimized_frames, duration=frame_duration, loop=0)
```
**Flow:** add_frame normalizes size/type → optional dedup at threshold (0.9995 default = only nearly identical go; 0.98 = aggressive) compares each frame against the last KEPT frame, so runs of similar frames collapse to their first member → emoji path resizes >128px to 128² LANCZOS, caps colors ≤48, strides frames to ~12 via keep_every = len//12 → global-palette quantization → write with loop=0.
**Invariant:** Comparison anchor is the last *kept* frame (chained), NOT the previous raw frame — a slow drift survives dedup frame-by-frame but each kept frame re-anchors the chain. Removal is opt-in (`remove_duplicates=False`) and **never compensates duration**: with uniform `1000/fps`, every dropped or strided frame shortens the animation by one tick — dedup trades fidelity-of-timing for bytes, deliberately.
**Probe:** repo-root deterministic probes (executed 2026-08-26): `grep -n 'threshold: float = 0.9995' skills/slack-gif-creator/core/gif_builder.py` = line 124; `grep -n 'deduplicated\[-1\]' skills/slack-gif-creator/core/gif_builder.py` = line 143; `grep -n '1000 / self\.fps' skills/slack-gif-creator/core/gif_builder.py` = line 224.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "skills", file_pattern: "*slack-gif*", limit: 50 });
```
Live result 2026-08-26: `GIFBuilder` Class :17–269 with `__init__ :20-32`, `add_frame :34-52`, `deduplicate_frames :124-158` (+ has_more pages carrying `save`).

## Verdict
Adopt chained-anchor mean-abs-diff dedup with a strictness ladder (0.9995 preserve-subtle / 0.98 aggressive) and the keep-every-nth emoji subsample for any frame-based animation pipeline. Adapt thresholds and the 12-frame/48-color targets to your platform limits. Omit the PIL paint recipes (easing curves, draw_* helpers — standing boundary). Caveat: no upstream tests exist for this module (deterministic probes substitute); the duration-shortening behavior is source-confirmed at pin main@3b3fad96af16 and must be ported consciously, not "fixed" silently.
