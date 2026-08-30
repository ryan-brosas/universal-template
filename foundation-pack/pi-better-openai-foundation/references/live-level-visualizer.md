<!-- capsule-v2 -->
# Level-decay visualizer — how do you render an audio spectrum widget that stays smooth between level updates and never leaks an interval?

**Source:** pi-better-openai MIT `main@86814e9047996abba08e4c907e23286329196fe0`; Codebase Memory `pi-better-openai`. **Question:** How does a TUI meter animate (decay, phase-colored spectrum, transcript line) inside a fixed-width panel?

## Visualizer
**Path/Symbol:** `src/live/visualizer.ts:class LiveVisualizer` (:51-277); decay loop :63-72; render cache :119-145; spectrum generator :255-276; width-1 degenerate :153-167; transcript sanitizer :33-41.
**Signature:** implements `Component { render(maxWidth): string[]; handleInput(data); invalidate(); dispose(); }`.
**Data Shape:** Inputs: phase enum, input level [0,1], current transcript; internal displayLevel + frame counter advanced by an unref'd 80ms interval.

### Decisive source
```ts
this.#animationInterval = setInterval(() => {
  this.#frame += 1;
  const decayed = this.#displayLevel * 0.84;
  this.#displayLevel = Math.max(this.#inputLevel, decayed < 0.001 ? 0 : decayed);
  this.#changed();
}, ANIMATION_INTERVAL_MS);
this.#animationInterval.unref?.();
```
Render is exact-width by contract — every returned line has `visibleWidth === maxWidth`, including the width≤1 degenerate panel and the footer's three-tier label fallback (full → short → bare border) (:239-245). The six-field cache key (width, phase, displayLevel, frame, role, text) makes repeat renders free. Transcript text is ANSI-stripped + control-char-blanked + whitespace-collapsed BEFORE layout (:33-41). Spectrum energy = `min(1, sqrt(display*5))` modulated by two per-column sine carriers, with a small idle oscillation during connecting.

**Flow:** level in → instant jump if above display, else exponential 0.84 decay per tick → frame bump invalidates cache → requestRender → render rebuilds bordered panel (top border / 2 spectrum rows / right-aligned truncated transcript / footer).
**Invariant:** Output lines are ALWAYS exactly maxWidth wide (test-pinned for widths 0..200) — padding math uses visibleWidth, not string length; the animation timer is unref'd AND cleared in dispose; raw transcript bytes are sanitized before entering themed output.
**Probe:** `tests/live-visualizer.test.ts` (:15 five-row fixed panel at every width, :49 transcript shown + no ANSI leak, :72 connecting-phase animation changes frames).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-better-openai", query: "LiveVisualizer generateSpectrum truncateFromStart", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt decay-loop + exact-width rendering + sanitize-before-layout. Adapt block glyphs/colors/theme keys to your TUI. Omit the keybinding set (host-specific).
