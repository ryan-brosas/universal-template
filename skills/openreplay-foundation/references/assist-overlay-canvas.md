<!-- capsule-v2 -->
# AnnotationCanvas + agent Mouse overlay — how do you draw on the user's screen and render a remote cursor that the tracker itself hides?

**Source:** openreplay AGPL-3.0 (tracker MIT) `main@99eb600`; Codebase Memory `openreplay`. **Question:** How are assist overlays kept out of the recording while staying visible to the user?

## Self-hiding overlays via data-openreplay-hidden
**Path/Symbol:** `tracker/tracker-assist/src/AnnotationCanvas.ts` (:1–82: z-index `2147483647-2`, `fadeOut` with `destination-out`, 4 s clear), `tracker/tracker-assist/src/Mouse.ts` (:7–65: cursor svg, name bubble truncated to 9 chars + '…', z-index 999998, `data-openreplay-hidden`), click injection `click(pos)` → `document.elementFromPoint` + synthetic mousedown.
**Signature:** `AnnotationCanvas.start/move/stop([x,y])`; `Mouse.move(pos)`; `Mouse.click(pos): Element`.
**Data Shape:** full-viewport fixed canvas; pointer-events none; red stroke width 8 round caps; fade = repeated 10 % alpha erase every 100 ms then clear at 4 s.

### Decisive source
```ts
this.canvas.setAttribute('data-openreplay-hidden', '1')   // tracker skips it
Object.assign(this.canvas.style, { position:'fixed', left:0, top:0,
  pointerEvents:'none', zIndex: 2147483647 - 2 })
...
private fadeOut() {
  const fadeStep = () => {
    this.ctx.globalCompositeOperation = 'destination-out'
    this.ctx.fillStyle = 'rgba(255,255,255,0.1)'
    this.ctx.fillRect(0,0,w,h)
    ... setTimeout(fadeStep, 100)
```

**Flow:** agent draws/moves → canvas strokes persist → stop triggers fade loop (progressive erase) → hard clear at 4 s; agent cursor is a DOM div positioned per move event, carrying a name badge; clicks dispatch real MouseEvents at `elementFromPoint(x,y)` so page handlers fire naturally — and since both overlays carry the hidden attribute, the tracker's sanitizer/observer excludes them from capture.
**Invariant:** Overlay elements MUST opt out of recording (attribute) or replay loops forever. Click injection must go through elementFromPoint + bubbling events, never direct `.click()` on coordinates.
**Probe:** `grep -c 'data-openreplay-hidden' tracker/tracker-assist/src/AnnotationCanvas.ts` → `1`; `grep -c 'destination-out' tracker/tracker-assist/src/AnnotationCanvas.ts` → `1`; `grep -c 'elementFromPoint' tracker/tracker-assist/src/Mouse.ts` → `5`; `grep -c "agentName.slice(0, 9)" tracker/tracker-assist/src/Mouse.ts` → `1`.
**Coverage:** clean.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openreplay", query: "AnnotationCanvas fadeOut Mouse elementFromPoint overlay", limit: 10 });
```

## Verdict
Adopt self-excluded overlay pattern + event-synthesized clicks. Adapt visuals. Omit drag-camera hooks when no 3D/canvas panning.
