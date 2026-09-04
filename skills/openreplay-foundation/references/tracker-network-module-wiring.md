<!-- capsule-v2 -->
# Tracker network-module wiring — how does one capture module serve proxy and legacy transports, iframes, privateMode, failuresOnly, and axios at once?

**Source:** OpenReplay AGPL-3.0 `main@99eb60032f70906f6887195c400f173c00a08522`; Codebase Memory `openreplay`. **Question:** What is the integration contract between the tracker App and the network proxies — which decisions live module-side (options, privacy, send-gating, time anchoring) versus proxy-side (interception mechanics)?

## Module defaults + five-callback contract
**Path/Symbol:** `tracker/tracker/src/main/modules/network.ts` — defaults (:63-78), `setSessionTokenHeader` (:94-101), `sanitize` (:103-120), `stringify` (:122-132), proxy delegation (:134-165), legacy prototype patching (:263-354), `getXHRRequestDataObject` expando (:34-42), iframe re-patch (:366-368).
**Signature:** `default (app: App, opts: Partial<Options>)`; `Options{ sessionTokenHeader, failuresOnly, ignoreHeaders, capturePayload, captureInIframes, sanitizer?, axiosInstances?, useProxy?, tokenUrlMatcher?, disabled? }`.
**Data Shape:** defaults: `failuresOnly=false`, `ignoreHeaders=['cookie','set-cookie','authorization']`, `capturePayload=false`, `captureInIframes=true`, `useProxy=true`. Per-XHR state rides an expando `xhr.__or_req_data__ = { body, headers }` ("this is 3x faster than using Map").

### Decisive source
```ts
function sanitize(reqResInfo: RequestResponseData) {
  if (!options.capturePayload || app.sanitizer.privateMode) {
    delete reqResInfo.request.body; delete reqResInfo.response.body
  }
  ...
}
// proxy send callback:
if (options.failuresOnly && message.status < 400) return
app.send(NetworkRequest(message.requestType, message.method,
  message.url, message.request, message.response, message.status,
  message.startTime + getTimeOrigin(),   // monotonic → wall-clock anchor
  message.duration, message.responseSize))
...
context.fetch = createNetworkProxy(..., app.sanitizer.privateMode ? true : options.ignoreHeaders, ...)
```

**Flow:** module builds the five callbacks once → useProxy path delegates all interception to `createNetworkProxy` (privateMode escalates ignoreHeaders to `true`) → legacy path (`useProxy:false`, deprecated with a debug warn) patches `XMLHttpRequest.prototype.open/send/setRequestHeader` directly and listens only to 'load' (no abort/timeout capture there) → `axiosInstances` bypasses prototype patching entirely and routes to axiosSpy → each finalized record passes the failuresOnly gate at SEND time, gets bodies deleted by sanitize when `!capturePayload || privateMode`, user sanitizer may veto, then timestamps anchor as `startTime + getTimeOrigin()` before `app.send`. `captureInIframes` re-runs patchWindow per new context via `app.observer.attachContextCallback`.
**Invariant:** All policy (what to keep, who to filter, when to send) lives module-side; proxies stay generic. Body deletion must happen BEFORE any transport can serialize the record. The legacy path is a strict subset of the proxy path — never add new capabilities there.
**Probe:** deterministic anchors on decisive lines: `grep -c '__or_req_data__' tracker/tracker/src/main/modules/network.ts` → `3`; `grep -c attachContextCallback ...network.ts` → `1`; `grep -c 'getTimeOrigin()' ...network.ts` → `3`. No dedicated upstream test file for this module at pin (coverage caveat; jest suite lives under tracker/tracker/test for other modules).
**Coverage:** network.ts `no_recorded_issue`/`metadata_match` @ gen 2026-08-25T20:08:30Z.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openreplay", query: "network module patchWindow useProxy axiosSpy failuresOnly capturePayload iframes", limit: 10 });
```
(Executed at pin: top hits modules/network.ts:patchWindow :134-357 plus axiosSpy captureNetworkRequest/captureResponseData.)

## Verdict
Adopt the policy/mechanics split and the delete-before-send body gate. Adapt option names and the time-origin anchor to your SDK. Omit the legacy prototype-patching branch unless you must support environments without Proxy.
