<!-- capsule-v2 -->
# Drop animation choreography — final-keyframe capture, size morphing, and focus restore

**Source:** dnd-kit MIT `main@6fb57833026e06bb3925eef78316ba56d59749c8`; Codebase Memory `ext-ui-dnd-kit`. **Question:** How does the drop animation compute its target when the placeholder may differ in size, and what must happen on completion?

## runDropAnimation
**Path/Symbol:** `packages/dom/src/core/plugins/feedback/dropAnimation.ts:55-162`.
**Signature:** `runDropAnimation(ctx: {source, element, feedbackElement, placeholder, translate, moved, transition, alignment, styles, animation?, ...})`; custom animation = function receiving `{source, element, feedbackElement, placeholder, translate, moved}` returning promise|void; defaults `{duration: 250, easing: 'ease'}`.
**Data Shape:** keyframes over `translate` + optional `minHeight/maxHeight/minWidth/maxWidth` pairs (only when rounded intrinsic sizes differ); duration collapses to 0 under reduced-motion or when nothing moved.

### Decisive source
```ts
// pause the in-flight transition so it can be finished AFTER our animation
const [, runningAnimation] =
  getFinalKeyframe(ctx.feedbackElement, (keyframe) => 'translate' in keyframe) ?? [];
runningAnimation?.pause();

const target = ctx.placeholder ?? ctx.element;
const current = new DOMRectangle(ctx.feedbackElement, options);
const currentTranslate = parseTranslate(getComputedStyles(...).translate) ?? ctx.translate;
const final = new DOMRectangle(target, options);
const delta = Rectangle.delta(current, final, ctx.alignment);
const finalTranslate = { x: currentTranslate.x - delta.x,
                         y: currentTranslate.y - delta.y };
const heightKeyframes = Math.round(current.intrinsicHeight) !== Math.round(final.intrinsicHeight)
  ? { minHeight: [`${current.intrinsicHeight}px`, `${final.intrinsicHeight}px`],
      maxHeight: [`${current.intrinsicHeight}px`, `${final.intrinsicHeight}px`] } : {};
...
}).then(() => {
  ctx.feedbackElement.removeAttribute(DROPPING_ATTRIBUTE);
  runningAnimation?.finish();        // jump the paused transition to its end
  ctx.cleanup();
  requestAnimationFrame(ctx.restoreFocus);   // keyboard drags re-focus after paint
});
```

**Flow:** status flips to dropped → Feedback's effect defers through `renderer.rendering` → custom functions bypass everything and own cleanup; the default path pauses any running translate transition, measures current vs placeholder geometry (alignment-aware delta), animates translate + min/max size toward the slot, then removes the dropping attribute, FINISHES the paused transition (so no residual interpolation fights), runs cleanup (placeholder swap-back happens here), and restores focus a frame later.
**Invariant:** the paused-then-finish dance is required because cancelling would snap while letting it run would fight the drop tween; `moved=false` ⇒ zero-duration (no phantom wiggle for plain click-drag-release); alignment shifts the delta so right/bottom-aligned lists animate to the correct slot.
**Probe:** referenced contract pinned by drag-event-order test teardown expectations; full animation path is DOM-timing heavy — no direct unit file upstream (coverage caveat).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ui-dnd-kit", query: "runDropAnimation", name_pattern: "^runDropAnimation$", limit: 10 });
```

## Verdict
Adopt pause/finish composition, size-morph keyframes, and rAF-deferred focus restore; adapt easing/duration defaults to your design system; omit size morphing for fixed-height rows.
