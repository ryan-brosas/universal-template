<!-- capsule-v2 -->
# Start-response client contract — what must the browser do with `/v1/web/start`'s response before recording may begin?

**Source:** OpenReplay AGPL-3.0 (tracker MIT) `main@99eb60032f70906f6887195c400f173c00a08522`; Codebase Memory `openreplay`. **Question:** How does the client turn an admission response into a running session (clock correction, token rotation, socket-only switch, canvas flags)?

## App._start admission sequence
**Path/Symbol:** `tracker/tracker/src/main/app/index.ts:_start` (:1480–1730); clock fold `timestamp()` (:1042–1044); rotation broadcast (:1620–1625).
**Signature:** `private async _start(startOpts: StartOptions = {}, resetByWorker = false, conditionName?: string): Promise<StartPromiseReturn>`.
**Data Shape:** request `{...trackerInfo, timestamp, doNotRecord:false, bufferDiff, userID, token?, condition?, assistOnly?, width/height/referrer}`; response `{token, userUUID, projectID, beaconSizeLimit, compressionThreshold, delay, sessionID, startTimestamp, user*, canvasEnabled/canvasQuality/canvasFPS/framesSupport, assistOnly, protocolVersion}`.

### Decisive source
```ts
if (typeof token !== 'string' || typeof userUUID !== 'string' ||
    (typeof startTimestamp !== 'number' && typeof startTimestamp !== 'undefined') ||
    typeof sessionID !== 'string' || typeof delay !== 'number' ||
    (typeof beaconSizeLimit !== 'number' && typeof beaconSizeLimit !== 'undefined')) {
  const reason = `Incorrect server response: ${JSON.stringify(r)}`
  this.signalError(reason, []); return UnsuccessfulStart(reason)
}
this.delay = delay                                   // server clock correction…
this.session.setSessionToken(token, this.projectKey)
if (sessionToken && sessionToken !== token) {        // token ROTATED:
  this.bc?.postMessage({ type: proto.reset, token }) // …force every other tab to restart
}
...
if (socketOnly) { this.socketMode = true; this.worker?.postMessage('stop') }
else { this.worker?.postMessage({ type: 'auth', token, beaconSizeLimit, protocolVersion }) }
```

**Flow:** worker gets `{type:'start', pageNo, timestamp: coldStartTs||now}` BEFORE the fetch → non-200 ⇒ `UnsuccessfulStart('Server error: <status>. <body>')` with the literal `'canceled'` body passed through → typed validation ladder rejects malformed payloads wholesale (never partial-start) → on success: `delay` is folded into every subsequent `timestamp() = now() + this.delay`; sessionID/startTimestamp/projectID land in Session; `socketOnly` flips the instance to assist-socket mode and STOPS the batch worker; otherwise the worker is authorised with token + beaconSizeLimit + protocolVersion → `TabChange` fires only when resuming (`!isNewSession && token === sessionToken`), metadata re-sends unconditionally for fresh sessions → startCallbacks/userStartCallback → state Active → CanvasRecorder created only if `canvasEnabled && !disableCanvas`.
**Invariant:** The client treats the admission response as UNTRUSTED until every wire-critical field passes its typeof ladder — one bad field aborts the whole start. Server `delay` is the ONLY authority on clock skew (client timestamps are meaningless without it). Token rotation is a broadcast event, not local state: sibling tabs holding the old token receive `proto.reset` and restart rather than silently split-braining into two sessions.
**Probe:** `grep -n 'Incorrect server response' tracker/tracker/src/main/app/index.ts` → :1613; `grep -n "proto.reset" …/app/index.ts` → :446, :1622; `grep -n 'No worker found' …/app/index.ts` → :1496 (verified live at pin).
**Direct test:** none in-repo for `_start`; server-side twin of this contract is pinned by `session-start-admission.md`.

## Get live surrounding code
**Retrieve (executed):**
```ts
await mcp.codebase_memory.search_graph({ project: "openreplay", query: "start session token response validation compressionThreshold socketOnly", limit: 6 });
```
→ resolves `Session.setSessionToken :133-136` / `Session.getSessionToken :115-127` (token store twins of this contract).

## Verdict
Adopt the typed whole-or-nothing response ladder, server-delay timestamp folding, and rotate-broadcast-restart semantics as pure behavior. Adapt field names/thresholds to your ingest API. Omit the socketOnly branch if you have no live-assist mode.
