<!-- capsule-v2 -->
# useScroll scroll-linked values — how does scroll position become motion values without re-render storms?

**Source:** framer-motion (Motion) MIT `main@1b037b0032578b52af94b06ff3920bfa0aaa5e36`; Codebase Memory `ext-ui-framer-motion`. **Question:** What does the hook measure, which events drive it, and what are the default value ranges a consumer can rely on?

## Scroll info producer
**Path/Symbol:** `packages/framer-motion/src/value/use-scroll.ts:useScroll` + `value/scroll/*` (info producers, event wiring). Graph seam: `search_graph "useScroll scrollInfo"` resolves the family.
**Signature:** `useScroll({container?, target?, axis?="y", offset?=["0 0","1 1"]?, layoutEffect?=true}) -> { scrollX, scrollY, scrollXProgress, scrollYProgress }`.
**Data Shape:** Progress values are `MotionValue<number>` in `[0,1]`; pixel values in px. Offsets are intersection descriptors like `"start end"` (target start meets container end).

### Decisive source (behavioral contract from hook surface + scroll plane)
```ts
// Scroll progress = how far the target has travelled through the container viewport,
// computed on scroll/layout events into preRender-coalesced updates:
//   scrollYProgress.set(progress(targetBounds, scrollOffsets))
// Values update OUTSIDE React render — consumers read via .on("change") or style binding.
```
Whole-file read of the scroll plane was deferred this pass (see work record NEXT-PASS TARGETS); the pinned contracts here are the public shape plus the derived-value scheduling it rides on (`references/derived-value-graph.md`). The decisive excerpt will be replaced by exact lines when the scroll plane is mined.

**Flow:** resolve container (default window/documentElement) and optional target → attach scroll/resize listeners → each event builds a scrollInfo measurement → progress/pixel MotionValues set inside frameloop coalescing → subscribers (style bindings, transforms) update without React renders. Layout-effect attachment by default so first paint already reflects current scroll.
**Invariant:** Progress is CLAMPED to [0,1] and derived from intersection offsets, not raw scrollTop — porting raw scrollTop division breaks nested/transformed containers. Pixel and progress pairs must update in the SAME frame or parallax consumers tear.
**Probe:** `packages/framer-motion/src/value/__tests__/use-scroll.test.tsx` exists upstream (runner blocked here — deps absent; recorded as caveat, not fabricated green).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ui-framer-motion", query: "useScroll scrollInfo scrollYProgress offset", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the four-value surface and [0,1]-clamped intersection-based progress; adapt listener plumbing to your framework. OMIT deeper claims until the dedicated pass mines `value/scroll/*` whole-file (queued as next-pass target #1) — this capsule intentionally stops at the confirmed public contract.
