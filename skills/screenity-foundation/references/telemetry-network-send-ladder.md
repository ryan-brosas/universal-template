<!-- capsule-v2 -->
# Telemetry network send ladder — how does the send degrade gracefully when auth, page lifetime, or the endpoint itself fail?

**Source:** screenity GPL-3.0 `master@e10e375fafa1680de99ca6db36536dd4a1f4f7d4`; Codebase Memory `screenity`. **Question:** What is the delivery ladder for a fire-and-forget diagnostic POST, and when should the client stop trying permanently?

## Token ladder → beacon-first unload sends → kill-switch on dead endpoints
**Path/Symbol:** `src/pages/CloudRecorder/CloudRecorder.jsx:sendUploadTelemetryNetwork` (:968-1011) with `resolveUploadTelemetryToken` (:680-709).
**Signature:** `sendUploadTelemetryNetwork(eventPayload) => Promise<void>`; `resolveUploadTelemetryToken() => Promise<string | null>`.
**Data Shape:** headers `{Content-Type, x-screenity-source: "extension", x-screenity-ext-version?, Authorization?}`; kill switch = `uploadTelemetryNetworkDisabledRef.current` boolean; beacon-eligible events: `upload_pagehide`, `upload_abandoned_on_unload`.

### Decisive source
```js
const sendUploadTelemetryNetwork = async (eventPayload) => {
  if (uploadTelemetryNetworkDisabledRef.current) return;
  try {
    const requestBody = await toUploadTelemetryRequest(eventPayload);
    if (!requestBody) return;
    const body = JSON.stringify(requestBody);
    const token = await resolveUploadTelemetryToken();
    // ...headers built; Authorization only if token...
    if ((eventPayload.event === "upload_pagehide" ||
        eventPayload.event === "upload_abandoned_on_unload") && navigator.sendBeacon) {
      const sent = navigator.sendBeacon(UPLOAD_TELEMETRY_ENDPOINT, new Blob([body], { type: "application/json" }));
      if (sent) return;
    }
    const res = await fetch(UPLOAD_TELEMETRY_ENDPOINT, { method: "POST", headers, credentials: "include", keepalive: true, body });
    if (res.status === 404 || res.status === 405 || res.status === 413) {
      uploadTelemetryNetworkDisabledRef.current = true;
    }
  } catch {}
};
```
Token ladder (:694-708): cached ref → `chrome.storage.local.get("screenityToken")` → `GET ${API_BASE}/auth/get-extension-token` (credentials include, accepts `token` or `extensionToken`) → null (send unauthenticated).

**Flow:** skip if disabled → build request (null request = silently unsent, per the allowlist capsule) → attach best-effort token → pagehide/unload events try `navigator.sendBeacon` first and return on `true` → otherwise POST with `keepalive: true` → 404/405/413 flips the permanent kill switch.
**Invariant:** (1) the kill-switch statuses are exactly "endpoint structurally gone or won't accept this body" (not-found / method-not-allowed / payload-too-large) — retrying those wastes battery forever, while 5xx/network errors must stay retriable and are just swallowed; (2) unload-class events must use beacon semantics because fetch may be killed with the tab, but a failed beacon falls back to keepalive fetch rather than dropping the event; (3) auth is best-effort — telemetry never blocks on login.
**Probe:** no upstream tests exist at pin. Deterministic anchors: grep CloudRecorder.jsx for `navigator.sendBeacon` gate at :989-999 and the triple-status check `res.status === 404 || res.status === 405 || res.status === 413` (:1007). Byte-exact at HEAD.

## Get live surrounding code
**Retrieve:**
```
search_graph(project="screenity", name_pattern="sendUploadTelemetryNetwork")
→ observed: 1 row, lines 968-1011, in=1 out=4 (exact match at pin)
```

## Verdict
Adopt the ladder ordering (kill-switch check → allowlist → token → beacon-for-unload → keepalive POST) and the exact 404/405/413 permanence rule. Adapt endpoint/header names and the token source chain. Omit the specific beacon-eligible event names if your host has no pagehide abandonment concept.
