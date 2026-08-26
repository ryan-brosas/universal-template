<!-- capsule-v2 -->
# video-preflight-battery — what does the renderer refuse to export, and why is privacy enforced at render time?

**Source:** browser-harness-js MIT `main@6b1894061e7a09a65a974d7d65a210b9a7ef06e0`; Codebase Memory `browser-harness-js`. **Question:** Which composition errors block export (vs warn), and where are the privacy gates so a porter doesn't ship a renderer that leaks secrets?

## Composition preflight battery
**Path/Symbol:** `skills/cdp/sdk/video-template.html` inline script → `preflightErrors` / `window.videoPreflight` (:109–168), export gate :937–943.
**Signature:** `window.videoPreflight() => { errors: string[], warnings: string[], frames: string[] }`.
**Data Shape:** ~18 hard-fail rules accumulate as strings into module-level `preflightErrors`; export REJECTS the promise with "Export blocked: …" when non-empty. Rules: schemaVersion must be 1; frameStyle must be "native" and readingWpm 380 unless deliberately changed; DURATION ≤ durationBudget (+0.001 epsilon); plan length 2–5; first beat = intro card ≥4s; last beat = outcome card with outcomes; every used frame (`b.frame`/`b.after`) present in `C.privacy.reviewedFrames`; card beats ≥ their computed read-time target; explanation points' labels joined must equal exactly `"observed|mistake|correction"`; synthetic chrome requires `authenticity.allowSyntheticChrome === true`; mask fill/stroke must match `/^#[0-9a-f]{6}$/i` (opaque); narration ≤7 words per beat; every non-card beat needs valid integer chapter + semantic route; raw `url` on a beat is an ERROR (`use route`); route/afterRoute matching `/@|[?#]|:\/\/|onmicrosoft|(?:tenant|user|object)[_-]?id|[0-9a-f]{8}-…-[0-9a-f]{4}-…/i` is an error.

### Decisive source
```js
const unsafeRoute = /@|[?#]|:\/\/|onmicrosoft|(?:tenant|user|object)[_-]?id|[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}/i;
...
for (const frame of usedFrames)
  if (!reviewedFrames.has(frame)) preflightErrors.push(`privacy review missing: ${frame}`);
...
if (b.url) preflightErrors.push(`beat ${i + 1} uses a raw url; use route`);
```

**Flow:** beats load → durations defaulted → validation collects errors → `exportVideo()` checks `preflightErrors.length` FIRST and rejects without touching MediaRecorder → only clean compositions play+record.
**Invariant:** Export is fail-CLOSED: any single preflight error blocks recording entirely; there is no override flag. Privacy review of frames and route sanitization are render-time gates, not optional lint — a porter who moves validation after capture ships a leak.
**Probe:** `grep -cF 'window.videoPreflight' skills/cdp/sdk/video-template.html` → 1; `grep -cF 'reviewedFrames.has(frame)' <same>` → 1; `grep -cF 'unsafeRoute.test(String(b.route' <same>` → 1; `grep -cF 'allowSyntheticChrome !== true' <same>` → 1 (106-probe sweep executed this pass).
**Retrieve:** search_code --project browser-harness-js --pattern "videoPreflight" (Module node resolves; BM25 search_graph has no tokens for prose symbols here).

## Verdict
Adopt the fail-closed export gate + reviewedFrames + unsafe-route regex as a unit (they encode the evidence-video honesty contract). Adapt the specific rule list/thresholds to your editorial style. Omit nothing if you keep the evidence pipeline — dropping the privacy half breaks the doctrine (see evidence-video-doctrine.md).
