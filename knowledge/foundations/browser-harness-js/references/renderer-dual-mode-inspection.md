<!-- capsule-v2 -->
# Renderer dual-mode inspection — how do you prove an animated canvas render passes its own preflight in BOTH normal and reduced-motion modes, and capture per-beat plus click-consequence visual evidence?

**Source:** browser-harness-js MIT `main@6b189406`; Codebase Memory `browser-harness-js`. **Question:** When your artifact is a time-animated canvas program, what inspection loop produces trustworthy evidence that every structural rule holds with animations ON and OFF, and that each recorded click AND its result are visible?

## inspectMode — one page walked twice through reload → ready-latch → assert → seek-then-capture
**Path/Symbol:** `skills/cdp/sdk/video-render.ts:inspectMode` (:270-304), on the micro-kernel `call` (:200-202) / `evaluate` (:204-214) / `waitForRenderer` (:266-268) / `capture` (:256-264); driven once per mode by `review` (:417-418).
**Signature:** `async function inspectMode(page: BrowserPage, name: string, reduced: boolean, samples: Array<{time:number;label:string}>, reviewDirectory: string): Promise<Json>` — returns `{ preflight, clicks, captures, clickCaptures }`.
**Data Shape:** `page` is a disposable-context CDP page (`{session,targetId,sessionId,browserContextId}`); every wire call is `bounded(session._call(method, params, {sessionId}), method)` (30s default timeout). `evaluate` THROWS on `exceptionDetails` rather than returning an error-shaped value.

### Decisive source
```ts
await call(page, 'Emulation.setEmulatedMedia', {
  media: '',
  features: reduced ? [{ name: 'prefers-reduced-motion', value: 'reduce' }] : [],
});
await call(page, 'Page.reload', { ignoreCache: true });
await waitForRenderer(page);                                   // window.videoReady() truthy latch
const preflight = await evaluate<Json>(page, 'window.videoPreflight()');
const clicks = await evaluate<Json[]>(page, 'window.clickVisibility()');
for (let index = 0; index < samples.length; index++) {
  const sample = samples[index]!;
  await evaluate(page, `window.seek(${JSON.stringify(sample.time)})`);
  await capture(page, join(reviewDirectory, `${name}-beat-${String(index + 1).padStart(2,'0')}.png`));
}
for (let index = 0; index < clicks.length; index++) {
  const click = clicks[index]!;
  for (const [state, key] of [['click', 'time'], ['result', 'resultTime']] as const) {
    await evaluate(page, `window.seek(${JSON.stringify(click[key])})`);
    await capture(page, join(reviewDirectory, `${name}-click-${String(index+1).padStart(2,'0')}-${state}.png`));
  }
}
```

**Flow:** set the media feature for the mode → hard-reload ignoring cache so the emulation applies from first paint → wait the renderer's own readiness latch → run the template's preflight and click-visibility audits in-page → for each review sample seek the pure-playhead to the exact time and screenshot → for each click capture TWO frames (the click instant and the result instant, because consequences land later than actions) → return everything to `review`, which re-runs the whole function with `reduced=true` and merges errors as `"${mode}: …"`.
**Invariant:** NOTHING IS ASSERTED ONCE. Every structural claim (preflight rules, click-inside-safe-viewport) must hold in normal AND `prefers-reduced-motion: reduce` modes on a freshly reloaded page; any single mode's error fails the whole review (exit code 1), while warnings only report. Screenshots use `captureBeyondViewport: true` so nothing depends on the live viewport at capture time.
**Probe:** no direct test drives this plane (grep over all three suites returns nothing — needs live Chromium). Deterministic probe executed pass 6: `grep -n "prefers-reduced-motion\|window.videoPreflight()\|window.clickVisibility()" skills/cdp/sdk/video-render.ts` (:279, :283, :284).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "browser-harness-js", query: "inspectMode", limit: 3, fields: ["signature", "name", "file"] });
// EXECUTED pass 6: resolves browser-harness-js.skills.cdp.sdk.video-render.inspectMode @ video-render.ts:270-304;
// trace_path inbound shows exactly one caller: review (:397).
```

## Verdict
Adopt the dual-mode + two-frame-click evidence pattern and the mode-prefixed error aggregation for any generated visual artifact that ships with its own rule audit; adapt the readiness-latch expression and sample labels to your renderer; omit the template-specific `window.*` hooks unless you port the canvas template family too. Caveat: zero direct tests exercise this path — behavior is pinned by whole-file source reading and deterministic probes only; treat the 30s `bounded` default and PNG format as adapt-per-host.
