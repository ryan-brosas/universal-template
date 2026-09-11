<!-- capsule-v2 -->
# Derived camera geometry — where do two-frame click evidence and camera cuts come from: authoring or capture shape?

**Source:** browser-harness-js MIT `main@6b189406`; Codebase Memory `browser-harness-js`. **Question:** Who decides that a click beat shows before+after frames and when the virtual camera cuts?

## automaticClickPair from beforeFrame, eventTarget fallback, 58%-diagonal cameraCut

**Path/Symbol:** `skills/cdp/sdk/video.ts:compileAction` (:287-377) — `automaticClickPair` (:316,:318,:326-328), `eventTarget` (:209-217), camera/wide heuristics (:367-373); direct test `video.test.ts` :46-68.
**Signature:** `eventTarget(event): {x,y} | undefined`; the pair logic is a local const `automaticClickPair = CLICK_HELPERS.has(helper) && action.frameEvent == null && event.beforeFrame`.
**Data Shape:** recorder events carry EITHER `cursor {x,y}` (clicks) OR `box {x,y,w,h}` (typing); click events may also carry `beforeFrame` — the frame captured BEFORE the input dispatch; `CLICK_HELPERS = {'click_at_xy'}` (:62).

### Decisive source
```ts
const automaticClickPair = CLICK_HELPERS.has(helper) && action.frameEvent == null && event.beforeFrame;
const beat: Json = {
  frame: automaticClickPair ? event.beforeFrame : frameEvent.frame,
  ...
};
...
} else if (automaticClickPair) {
  beat.after = event.frame;                       // after = the frame captured WITH the click
}
```
and the movement heuristics:
```ts
const target = eventTarget(event);                 // cursor, else box @ x + w*0.3, y + h/2
if (action.context === true && !beat.click && !beat.type) beat.wide = true;
else if (target && previousTarget) {
  const distance = Math.hypot(target.x - previousTarget.x, target.y - previousTarget.y);
  const diagonal = Math.hypot(Number(viewport.w), Number(viewport.h));
  if (distance > diagonal * 0.58) beat.cameraCut = true;
}
```

**Flow:** a brief action naming a click event with NO explicit `frameEvent` but whose captured event has `beforeFrame` silently upgrades to two-frame evidence (frame=before, after=post-click) → otherwise `frameEvent`/`event` picks the single frame, and an explicit `afterEvent` adds `after` → the beat's pointer target is cursor coords, falling back to the box's 30%-width point (left-of-center, where labels usually sit) → if that target jumps more than 58% of the viewport diagonal from the previous beat's target the template receives `cameraCut:true` instead of panning across the screen → `context:true` on non-input actions asks for a wide shot.
**Invariant:** (1) Click evidence is structural, not editorial: because the RECORDER captures before/under-click frames, the compiler can guarantee every default click shows state-before AND state-after without the brief author remembering to ask. (2) Camera motion is derived from geometry so the brief stays declarative — authors name events, the compiler decides pan vs cut. (3) The 0.58 factor means anything past mid-screen cuts rather than panning; it is tuned to HOUSE_STYLE's autoZoom/motion constants, not universal.
**Probe:** DIRECT test `'recording initialization hides typing and hashes exact evidence'` (video.test.ts :54-57): action `{event:2}` (a click_at_xy event with `beforeFrame:'0001.jpg'`, `frame:'0002.jpg'`) compiles to `beats[1].frame === '0001.jpg'`, `beats[1].after === '0002.jpg'`, `beats[1].click === true`. Deterministic pins: `grep -n "automaticClickPair\|cameraCut\|Math.hypot" skills/cdp/sdk/video.ts` → :316/:318/:326/:372/:370-371.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "browser-harness-js", query: "eventTarget", limit: 3, fields: ["lines"] });
// resolves video.eventTarget @ video.ts:209-217 (single hit)
```

## Verdict
Adopt capture-shape-derived evidence pairs (record once at the source, derive structure at compile time) for any recorder-to-renderer pipeline; adapt the 30% box anchor and 0.58 cut threshold to your camera model; omit the wide/context flag only if your grammar has no zoom concept.
