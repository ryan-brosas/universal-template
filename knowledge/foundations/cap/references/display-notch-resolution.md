<!-- capsule-v2 -->
# display-notch-resolution — When is the display notch recorded into meta, and how is it rebased for area captures?

**Source:** cap AGPL-3.0 `main@0ce9e67516b14449c4263c0b173c85c40f30421b`; Codebase Memory `ext-cap`. **Question:** For which capture targets does a notch position exist, and what are the exact rejection conditions for area captures?

## Full-display captures carry the notch; area captures only when FULLY contained with top edge at 0; window/camera never
**Path/Symbol:** `crates/recording/src/capture_pipeline.rs:549-602` (`resolve_display_notch`, `resolve_area_display_notch`); consumed once at actor spawn (`studio_recording.rs:894` — "Resolved once at recording start: the display can be disconnected, or its mode changed, by the time the recording stops").
**Signature:** `pub fn resolve_display_notch(target: &ScreenCaptureTarget) -> Option<DisplayNotch>`; `fn resolve_area_display_notch(notch: NotchGeometry, display_size: LogicalSize, bounds: LogicalBounds) -> Option<DisplayNotch>`.
**Data Shape:** `DisplayNotch { x, width, height }` in FRACTIONS of the captured frame; source notch geometry is fractions of the display.

### Decisive source
```rust
if area_width <= 0.0 || area_height <= 0.0 || area_top != 0.0 { return None; }  // notch lives on the top edge
let notch_left = notch.x * display_size.width();
let notch_right = notch_left + notch_width;
let notch_height = notch.height * display_size.height();
if area_left > notch_left || area_right < notch_right || area_bottom < notch_height {
    return None;   // partial intersection cannot be encoded by DisplayNotch
}
Some(DisplayNotch {
    x: (notch_left - area_left) / area_width,
    width: notch_width / area_width,
    height: notch_height / area_height,
})
```

**Flow:** Window targets return None (the window surface moves; no stable notch). Area targets rebase the display-fractional notch into frame-fractional coordinates ONLY when the area fully contains it AND starts at the top edge (area_top == 0.0). The value is resolved ONCE before the actor spawns and stamped onto every segment's meta.
**Invariant:** A partially-cropped notch must be OMITTED, not approximated — `DisplayNotch` can't encode a cropped source shape, and a wrong notch silently misrenders camera-hole overlays. Resolve-at-start prevents mid-recording display changes from corrupting coordinates.
**Probe:** `crates/recording/src/capture_pipeline.rs:619-656` — tests `area_containing_the_full_notch_rebases_it` (asserts exact rebased fractions x:0.25,width:0.5,height:0.4) + `partially_intersected_notches_are_omitted`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-cap", query: "resolve_display_notch resolve_area_display_notch", limit: 10 });
```

## Verdict
Adopt the containment test (top-edge anchored, full inclusion) and fraction-rebasing math. Adapt geometry types.
