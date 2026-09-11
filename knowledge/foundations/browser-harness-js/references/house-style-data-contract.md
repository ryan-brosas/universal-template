<!-- capsule-v2 -->
# House-style data contract — why is editorial style versioned DATA embedded in the artifact instead of constants in the renderer?

**Source:** browser-harness-js MIT `main@6b189406`; Codebase Memory `browser-harness-js`. **Question:** How do compiler and renderer stay on one editorial style without importing shared code?

## HOUSE_STYLE consumed both sides; composition header records schemaVersion = style.version

**Path/Symbol:** `skills/cdp/sdk/video.ts:HOUSE_STYLE` (:25-51); consumption `compileBrief` (:436-437, :488-506); enforcement downstream `video-template.html` preflight (contract in video-preflight-battery: frameStyle native + readingWpm 380).
**Signature:** `const HOUSE_STYLE: Json = { version, frameStyle, readingWpm, background[], cursorStart, pacing{…}, motion{…}, privacy{ pad, mask{fill,stroke,radius} } }`.
**Data Shape:** three sub-objects split by consumer: `pacing` is read ONLY by the compiler (durations/budget), `motion`/`cursorStart`/`background` are read ONLY by the template's camera/paint code, `privacy.pad/mask` re-appears in the composition header for mask geometry; `version` becomes `schemaVersion` (:489).

### Decisive source
```ts
export const HOUSE_STYLE: Json = {
  version: 1,
  frameStyle: 'native',
  readingWpm: 380,
  background: ['#efece4', '#dce7e7'],
  cursorStart: { x: 700, y: 280 },
  pacing:   { captionBaseSeconds: 0.35, captionSecondsPerWord: 0.2, rawToCardHoldSeconds: 0.55,
              baseDurationBudget: 22, extraActionSeconds: 1.25, extraExplanationSeconds: 3,
              maximumDurationBudget: 32 },
  motion:   { autoFollow: true, autoZoom: 1.7, cursorDuration: 0.48, zoomDuration: 0.42,
              panDuration: 0.55, wideScale: 0.78, reactionLag: 0.025, reactionFade: 0.04 },
  privacy:  { pad: 10, mask: { fill: '#ffffff', stroke: false, radius: 0 } },
};
```
```ts
const composition: Json = {
  schemaVersion: style.version,   // the compiled artifact RECORDS which style made it
  viewport: { w: viewport.w, h: viewport.h },
  cursorStart: style.cursorStart, frameStyle: style.frameStyle,
  readingWpm: style.readingWpm, pacing, durationBudget: budget,
  bg: style.background, plan, motion: style.motion,
  privacy: { reviewedFrames: reviewed, pad: style.privacy.pad, mask: style.privacy.mask },
  redact, beats,
};
```

**Flow:** the compiler reads `style.pacing`/`readingWpm` to compute every beat duration and the budget → it then embeds ALL style fields verbatim into the composition header alongside the beats → the template receives everything it needs (motion constants, cursor start, palette, pad/mask) through the composition itself — `video-template.html` never imports video.ts → the export-side preflight battery independently asserts `frameStyle === 'native'` and `readingWpm === 380`, so a hand-tweaked style fails loudly at export rather than silently changing the look.
**Invariant:** (1) Style is DATA with a version, not scattered literals: bumping `version` changes `schemaVersion` in every artifact compiled after it, making artifacts self-identifying. (2) Compiler and renderer couple only through the composition document — no shared import, so either side can be ported alone as long as the field contract survives. (3) Deliberate style deviation is possible but must survive TWO independent gates (brief compiles with any style object; export preflight pins the canonical values), which converts silent drift into an explicit error.
**Probe:** direct tests import HOUSE_STYLE explicitly (`video.test.ts` :9,:54,:75 pass it into compileBrief). Deterministic pins: `grep -n "version: 1\|readingWpm: 380\|autoZoom\|schemaVersion: style.version" skills/cdp/sdk/video.ts` → :26/:28/:42/:489.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "browser-harness-js", name_pattern: "^HOUSE_STYLE$", limit: 3, fields: ["lines"] });
// resolves video.HOUSE_STYLE Variable @ video.ts:25-51 (single hit; BM25 query "HOUSE_STYLE" returns 0 — tokenization caveat)
```

## Verdict
Adopt versioned style documents embedded into generated artifacts whenever two processes must agree on presentation without sharing code; adapt the field set to your medium; omit the export-side pin only if you accept that a stale renderer will silently render old styles.
