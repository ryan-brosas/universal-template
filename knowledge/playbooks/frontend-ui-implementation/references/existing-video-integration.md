# Reuse an existing website video

Use when replacing a website still with an authorized, already-published clip. A media URL proves neither the requested footage nor playable output. Verify identity, compatibility and runtime behavior separately.

## Extract and inspect before integration

1. Read the source page's `<video>`, `<source>` or embed metadata; do not guess a CDN URL or assume the first video is the requested one. Stop at access restrictions rather than changing transports to bypass them.
2. Inspect representative frames and the surrounding page context. Probe the downloaded source:

   ```sh
   ffprobe -v error -show_streams -show_format -of json source.mp4
   ```

   Check duration, dimensions, frame rate, codec, pixel/color format, audio and bytes. An MP4 container can carry HEVC; its extension is not evidence that target browsers can decode it.
3. Trace the destination component and every consumer of the old asset. Replace the intended media slot, not a shared file still used elsewhere. Preserve approved layout, crop and treatment unless changing them is in scope.

## Derive only what the browser contract needs

- Test the source against target browsers. If necessary, generate a supported rendition; H.264 with `yuv420p` and fast-start metadata is a useful MP4 option, not a universal export requirement. Choose dimensions from the rendered slot and quality budget, not the source's maximum resolution.
- Measure the result. Converting HEVC to H.264 can increase bytes even after downscaling; compatibility and compression are different outcomes.
- Derive the poster from an inspected source frame. Keep source URL, transformations, source/output sizes and hashes with project asset provenance, not in this playbook.
- Decide whether the film is decorative or informative before muting, hiding semantics or removing audio. Speech, captions and necessary visual information require equivalents. Control-free autoplay is not a reusable default; consult [accessibility guidance](../../wcag-accessibility-practices/README.md) for the project's target.

## Make decorative playback progressive

Render a real still fallback without JavaScript. Check reduced motion, data-saving signals where supported, and visibility **before assigning the video source**; `preload="none"` alone does not establish a no-download guarantee.

Start muted/inline playback only when allowed. Pause offscreen or hidden-page playback; respond to motion-preference changes. Restore the poster on genuine autoplay, network or decode failure. Distinguish an expected `AbortError` caused by pausing/unloading a pending play request from failure: it must not permanently disable later playback.

## Prove behavior, not configuration

- In target browsers, verify decoded dimensions and advancing `currentTime` or frame counts. If looping is required, cross the actual loop boundary; a `loop` attribute is insufficient.
- Exercise visibility pause/resume, preference changes, playback denial and failed media delivery. Inspect the fallback visually.
- Start fresh reduced-motion, save-data and no-JavaScript sessions. Confirm the poster renders and **no video request** occurs in modes intended to remain still; a paused element alone proves neither.
- Check desktop/mobile crop and overflow. Probe production asset paths and the running development site when their serving paths differ. Report untested browsers separately: screenshots and a passing build do not prove playback support.
