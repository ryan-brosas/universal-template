<!-- capsule-v2 -->
# Recorder bootstrap & consent-gated sampling — how does the recorder fetch config, sample sessions, and wait for the tracker's session before capturing?

**Source:** umami v3.3.1 / MIT @ master`ca661c70`; Codebase Memory `ext-umami`. **Question:** How are replay/heatmap captures started, sampled, and torn down — and why does capture wait for `window.umami.getSession().cache`?

## recorder-bootstrap-sampling
**Path/Symbol:** `src/recorder/index.js:bootstrap :678-713, waitForSession :636-645, startCaptures :647-668, shouldSample :318-322`; config validation twin `src/lib/recorder.ts:getRecorderConfig :11-44` with tests.
**Signature:** GET `/api/websites/<id>/recorder` → `{enabled,replayEnabled,heatmapEnabled,sampleRate,heatmapSampleRate,maskLevel,maxDuration,blockSelector}`; sampling `Math.random() <= value` (≥1 always, ≤0 never).
**Data Shape:** defaults sampleRate=0.15, heatmapSampleRate=0.15, maskLevel='moderate', maxDuration=300000ms.

### Decisive source
```js
const waitForSession = (callback, attempts = 0) => {
  if (attempts > 50) return;                        // ~5s max, then give up silently
  if (getSessionCache()) { callback(); return; }    // tracker's cache token = session exists
  setTimeout(() => waitForSession(callback, attempts + 1), 100);
};
...
const shouldRecordReplay  = replayEnabled && shouldSample(sampleRate);
const shouldRecordHeatmap = heatmapEnabled && shouldSample(heatmapSampleRate);   // INDEPENDENT draws
```

**Flow:** fetch remote config → both features off ⇒ abort before any DOM work → wait for page complete → poll for session cache token (recordings POST `x-umami-cache` which /api/record REQUIRES for sessionId/visitId) → start captures + unload flushers. Server re-validates every field via `getRecorderConfig` strict whitelist (tests pin rejection of `'true'` strings, NaN, unknown maskLevel).
**Invariant:** independent per-feature coin flips mean a session can have heatmap without replay — don't couple them. The cache-token wait is load-bearing: starting capture earlier yields events that all fail the missing-token check at :150 (`if (!cache) return`). `stopReplay` is idempotent via `replayStopped` and flushes BEFORE stopping the recorder fn.
**Probe:** `grep -c "test(" src/lib/recorder.test.ts` → 8 (:5-52 pin every config-validation rule incl. rounding :29 and Infinity rejection :31).
**Probe:** `grep -n "rounds finite maxDuration" src/lib/recorder.test.ts` → :29.

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "ext-umami", query: "bootstrap waitForSession startCaptures shouldSample", limit: 10 });
```
**(Retrieve:)**

## Verdict
Adopt server-driven feature config + session-readiness polling + independent sampling for any client capture SDK; adapt default rates; omit mask levels if your rrweb version differs.
