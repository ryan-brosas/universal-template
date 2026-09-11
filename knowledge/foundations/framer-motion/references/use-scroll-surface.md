<!-- capsule-v2 -->
# useScroll scroll-linked values: how does scroll position become motion values without re-render storms?

**Source:** framer-motion (Motion) MIT `main@1b037b0032578b52af94b06ff3920bfa0aaa5e36` (tag v13.1.1); Codebase Memory `ext-ui-framer-motion`. **Question:** What does the hook measure, which events drive it, and what are the default value ranges a consumer can rely on?

## Scroll info producer
**Path/Symbol:** `packages/framer-motion/src/value/use-scroll.ts:useScroll` + scroll plane `render/dom/scroll/*`: `track.ts`, `info.ts`, `on-scroll-handler.ts`, `offsets/index.ts`, `offsets/offset.ts`, `offsets/inset.ts`, `attach-function.ts` (v13.1.1 layout; the older `value/scroll/*` path does not exist at this pin). Graph seam: `search_graph "useScroll scrollInfo"` resolves the family.
**Signature:** `useScroll({container?, target?, axis?="y", offset?}): UseScrollOptions = {} -> { scrollX, scrollY, scrollXProgress, scrollYProgress }`; the `offset` default is `ScrollOffset.All` (`[[0,0],[1,1]]`, resolved inside `resolveOffsets`).

## Event plan (deferred pass #1, now closed)
Pinned at `main@1b037b0032578b52af94b06ff3920bfa0aaa5e36`.

v13.1.1 keeps the scroll engine under **`packages/framer-motion/src/render/dom/scroll/`** (not `value/scroll/*`):

- `track.ts:scrollInfo` attaches ONE scroll + resize listener per container; each event schedules a frameloop `read → preUpdate` measure/notify pair, so N consumers share measurement and update order:
  `scrollEvent → frame.read(measureAll) → frame.preUpdate(notifyAll)`.
- `info.ts:updateScrollInfo`: per axis `current = |scrollTop|`, `scrollLength = scrollHeight − clientHeight`, `progress = progress(0, scrollLength, current)` where motion-utils `progress` returns `(value−from)/(to−from)` and returns `1` when range is `0` (empty container). Velocity = `velocityPerSecond(delta, elapsed)`, zeroed when `elapsed > 50` ms.
- `offsets/`: `edge.ts` namedEdges start=0 / center=0.5 / end=1, px/%/vw/vh parsed by `resolveEdge`; `offset.ts:resolveOffset` returns `targetPoint − containerPoint`; presets Enter/Exit/Any/All are progress-pair arrays mapping `[edgeTarget, edgeContainer]`.
- `offsets/index.ts:resolveOffsets`: for target/offset scrolling, offsets are resolved to scroll positions, an `interpolate(offsets, defaultOffset, { clamp: false })` maps `current` to an unclamped progress, and the result is then hard-clamped: `info[axis].progress = clamp(0, 1, interpolate(current))`. `hasChanged` guards re-interpolate.
- `on-scroll-handler.ts:createOnScrollHandler.measure`: measures target offset (walking `offsetParent` chain for targetOffset), lengths, then `resolveOffsets` when target/offset is set, before notify.
- Native fast path (pass 2, verified): `scroll()` routes by callback arity — 2-arg callback OR target/offset tracking → `attachToFunction` (JS `scrollInfo`); plain 1-arg progress callback → `attachToAnimation` when it is a playback object (progression only). `attachToAnimation` (`attach-animation.ts`): uses native `ScrollTimeline` (no target, `supportsScrollTimeline()`) or `ViewTimeline` with named range (target + mappable `offsetToViewTimelineRange`); unmappable offsets fall back to the JS `scrollInfo` path via `get-timeline.ts:scrollTimelineFallback` (`currentTime.value = progress*100`). `observeTimeline` (`motion-dom/src/scroll/observe.ts`) polls the timeline in `frame.preUpdate` and calls the update only when `prevProgress` changed (dedupe).

**Invariant:** pixel and progress pairs must update in the same frame. They do, because `notify` carries a single `ScrollInfo` snapshot with both `current`, `offset`, `progress` on the same object; a port that splits the snapshot into separate calls will tear parallax consumers.

**Probe:** `packages/framer-motion/src/render/dom/scroll/__tests__/index.test.ts` (~900 lines, covers scroll handler fan-out and resolution) and `on-scroll-handler.test.ts` exist upstream; runner blocked here (no workspace deps), recorded as a caveat, not fabricated green.

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ui-framer-motion", query: "useScroll scrollInfo scrollYProgress offset", limit: 10, fields: ["signature", "name", "file"] });
```

## Capsule contract replacement (this pass)
Prior text deferred the scroll plane with `Whole-file read … deferred… value/scroll/*`. The verified contract supersedes that:
- Entry points: `useScroll` hook → `scroll()` (index.ts) → `attachToFunction` (progress-only) or `scrollInfo` (info consumers).
- Progress composition: pixel progress per axis + target/container offset interpolation (offset definitions `["start center"]`, percent/px/vw/vh); the offset lane hard-clamps to [0,1] via `clamp(0, 1, interpolate(...))` in `resolveOffsets`; the plain `scrollTop` lane uses `progress(0, scrollLength, current)` without an extra clamp.
- Velocity: 50 ms decay window; no smoothing; units px/sec (`velocityPerSecond`).
- DOM events feed the frameloop; multiple `useScroll` instances share one listener set per container via the `scrollListeners`/`resizeListeners` WeakMaps.

## Verdict
Adopt the frameloop-driven scroll listener fan-out, the shared per-container measurement, and the offset-string resolution including vw/vh/percent. Adapt the target-tracking `offsetParent` sum to the host's layout coordinates. Port progress semantics exactly: the target/offset lane is hard-clamped to [0,1] by `clamp(0, 1, interpolate(...))` in `resolveOffsets`; the plain lane uses unconditional `progress()` (returns 1 on empty-range). Omit the native ScrollTimeline acceleration unless the host supports WAAPI scroll timelines.
