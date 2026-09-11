<!-- capsule-v2 -->
# Viewer-side reduced-motion collapse — how do you honor the VIEWER's prefers-reduced-motion without destroying timing structure, click evidence, or division safety?

**Source:** browser-harness-js MIT `main@6b1894061e7a09a65a974d7d65a210b9a7ef06e0`; Codebase Memory `browser-harness-js`. **Question:** When the viewer's OS requests reduced motion, what exactly may collapse (tweens) versus what must survive (reveal schedule, geometry, divisors, effect gates) in a deterministic canvas composition?

## Motion has two independent inputs; only TIME collapses

**Path/Symbol:** `skills/cdp/sdk/video-template.html` header latch (`MOTION`, `REDUCED_MOTION`) and its consumers (`PUNCH_S`/`DRIFT_MAX`/`CUR_S`, `glideDelay`/`clickTime`, camera kernel, caption + narration reveals) (:36–49, :217–225, :329–340, :352, :394–395, :532–533, :778, :842–847).
**Signature:** `const REDUCED_MOTION = matchMedia("(prefers-reduced-motion: reduce)").matches;` — every consumer branches on this single latch or on constants derived from it.
**Data Shape:** Author intent rides in the composition header (`MOTION = C.motion || {}`, :36); the viewer's OS preference is latched ONCE at page load (:38). Identical composition bytes therefore render differently per viewer environment — a render property, not a bug.

### Decisive source
```js
const MOTION = C.motion || {};
const REDUCED_MOTION = matchMedia("(prefers-reduced-motion: reduce)").matches;
const PUNCH_S   = REDUCED_MOTION ? 0 : (MOTION.zoomDuration ?? 0.46);
const DRIFT_MAX = REDUCED_MOTION ? 0 : (MOTION.panDuration  ?? 0.58);
const CUR_S     = REDUCED_MOTION ? 0 : (MOTION.cursorDuration ?? 0.52);
const AUTO_ZOOM = MOTION.autoZoom ?? 1.7;              // geometry NEVER collapses (:42-47)
...
const REACTION_LAG  = REDUCED_MOTION ? 0     : (MOTION.reactionLag  ?? 0.025);
const REACTION_FADE = REDUCED_MOTION ? 0.001 : (MOTION.reactionFade ?? 0.04);  // divisor!
```

**Flow:** page load → latch OS preference once → zeroed durations make every easing ternary select FINAL STATE with no per-site branch (`k = dur ? easeOutQuint(clamp(lt/dur,0,1)) : 1` :330 where `dur` is built from PUNCH_S/DRIFT_MAX :329; cursor glide `k = glide ? easeOutQuint(...) : 1` :225 with `glide = Math.min(CUR_S, dur*0.42)` = 0) → `clickTime(i)` (:219 = `glideDelay + glideDuration + 0.035`, each term reading collapsed constants) compresses toward beat start automatically → narration points KEEP their pacing schedule (`revealAt = firstReveal + n*revealGap` :842) and still stagger on narration time; only the ease/slide dies (`k = lt < revealAt ? 0 : REDUCED_MOTION ? 1 : easeOutQuart(...)` :843; `slide = REDUCED_MOTION ? 0 : 14*(1-k)` :847; captions likewise `k = REDUCED_MOTION ? 1 : easeOutQuart(...)` :778) → error shake is gated off as an EFFECT, not a duration (`if (b.errorMotion && !REDUCED_MOTION) { ... } else cam.shake = 0` :337–340).

**Invariant:** Collapse removes TWEENS, not TIMING STRUCTURE. Geometry (`AUTO_ZOOM`/`WIDE_SCALE`/`CLICK_SAFE` :42–47) never collapses — framing/layout are preference-independent. Exactly ONE collapsed value stays non-zero: `REACTION_FADE → 0.001` (:49) because it is a DIVISOR (`k = clamp((lt-at)/REACTION_FADE, 0, 1)` :533 drives the after-frame alpha ramp; visibility gate `lt >= at + REACTION_FADE` :394–395) — a literal 0 divides by zero and poisons the ramp with ±∞/NaN instead of a bounded fade, silently killing the after-frame half of the two-frame click evidence (whose `resultTime` arithmetic :352 also routes through REACTION_LAG+REACTION_FADE). The same divisor discipline guards the reveal spacing as `Math.max(0.001, revealGap)` (:837).
**Probe:** no direct test drives the template plane (needs live Chromium — consistent with the renderer-plane caveat). Deterministic probe executed this pass at pin 6b18940: grep `REDUCED_MOTION` over `skills/cdp/sdk/video-template.html` → exactly 12 sites (:38;39;40;41;48;49;217;219;337;778;843;847); decisive ranges read directly (:28–65, :198–239, :318–362, :385–400, :520–541, :768–791, :830–855). Adversarial check executed BEFORE authoring: BM25 "respect viewer prefers-reduced-motion accessibility setting when animating" ranks recording/generated AX wrappers first — the seam is unretrievable without this capsule.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_code({ project: "browser-harness-js", pattern: "REDUCED_MOTION", path_filter: "video-template\\.html", context: 1 });
```
(Symbol search cannot see template prose: search_graph ranks generated.ts `Animation.*` wrappers and the html surfaces only as one Module node spanning lines 1–973.)

## Verdict
Adopt the two-input split (author intent vs viewer OS latch), tween-not-timing collapse routed through SHARED duration constants, schedule-preserving reveals, effect-gated shake, and the bottom-out-at-0.001 rule for any collapsed constant that reaches a denominator. Adapt durations/insets to your own motion vocabulary. Omit nothing structural: collapsing a divisor constant to literal 0 breaks after-frame evidence only under reduce — the exact mode your accessibility reviewer will inspect. This viewer-dependence is why renderer-dual-mode-inspection asserts everything twice: Emulation.setEmulatedMedia reduce + Page.reload flips THIS latch mid-review, so every structural claim must hold in BOTH renderings of identical bytes. Coverage caveat: template plane carries no direct tests; evidence is direct-range reads plus executed deterministic probes at pin 6b18940.
