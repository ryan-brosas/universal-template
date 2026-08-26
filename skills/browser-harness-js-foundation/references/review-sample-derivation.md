<!-- capsule-v2 -->
# Review sample derivation — which playhead times should a reviewer screenshot when beats have radically different shapes (point-list explanations vs cards)?

**Source:** browser-harness-js MIT `main@6b189406`; Codebase Memory `browser-harness-js`. **Question:** How do you choose screenshot times for human review so every narration point is visually evidenced without a wasteful fixed-fps grid?

## reviewSamples — content-aware per-beat sample times, clamped and accumulated
**Path/Symbol:** `skills/cdp/sdk/video-render.ts:reviewSamples` (:60-81) with `round` (:83-85); consumed only by `review` (:402).
**Signature:** `function reviewSamples(composition: Json): Array<{ time: number; label: string }>` — `time` is absolute (seconds, ms-rounded), `label` is `"beat N"` or `"beat N · <point label>"`.
**Data Shape:** input is the compiled composition (`beats[]`, each `{ kind?, dur?, card?, points?: [{label}] }`); output array length = Σ(1 per beat + extra samples for explanation points).

### Decisive source
```ts
let start = 0;
(composition.beats || []).forEach((beat: Json, index: number) => {
  const duration = Number(beat.dur || 0);
  if (beat.kind === 'explanation' && Array.isArray(beat.points) && beat.points.length) {
    const first = 1.1;
    const finalHold = 3;
    const span = Math.max(0, duration - first - finalHold);
    const gap = span / Math.max(1, beat.points.length - 1);
    beat.points.forEach((point: Json, pointIndex: number) => {
      const local = Math.min(Math.max(0.05, duration - 0.05), first + pointIndex * gap + 0.2);
      samples.push({ time: round(start + local), label: `beat ${index + 1} · ${point.label || pointIndex + 1}` });
    });
  } else {
    const local = Math.min(Math.max(0.05, duration - 0.05),
      beat.card ? 1 : Math.max(0.12, Math.min(0.5, duration / 2)));
    samples.push({ time: round(start + local), label: `beat ${index + 1}` });
  }
  start += duration;
});
```

**Flow:** walk beats accumulating `start += dur` → explanation beats with points get ONE sample PER POINT, evenly spaced across the span between a 1.1s lead-in and a 3s final hold, biased +0.2s past each slot → every other beat gets a single early sample (card beats at 1s; plain beats at half duration clamped to [0.12, 0.5]s) → every sample time is clamped inside `(0.05, dur − 0.05]` of its own beat before being offset to absolute time.
**Invariant:** SAMPLING FOLLOWS CONTENT, NOT CLOCK. A fixed-fps or fixed-interval grid would either miss narration points or drown the reviewer in near-identical frames; here the count of screenshots is a function of how many distinct claims the beat makes. The clamp guarantees no sample ever lands on a beat boundary (where the pure-playhead render is mid-transition), and ms-rounding keeps times stable across JSON serialization.
**Probe:** no direct test (pure function inside an untested plane). Deterministic probe executed pass 6: `grep -n "finalHold\|points.length - 1\|duration / 2" skills/cdp/sdk/video-render.ts` (:67-69, :75).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "browser-harness-js", query: "reviewSamples", limit: 3, fields: ["signature", "name", "file"] });
// EXECUTED pass 6: resolves browser-harness-js.skills.cdp.sdk.video-render.reviewSamples @ video-render.ts:60-81
// (callers=1 -> review).
```

## Verdict
Adopt content-proportional review sampling (one frame per claim, boundary-clamped, cumulative absolute times) for any timeline artifact a human must audit; adapt the 1.1s/3s/+0.2s pacing constants and the card-vs-plain early-sample rule to your beat grammar; omit nothing from the clamp — removing it puts review frames on transitions where masks and labels are mid-animation. Caveat: untested by direct suites (whole-file source read + deterministic probes only); the constants encode this repo's HOUSE_STYLE durations, not universal values.
