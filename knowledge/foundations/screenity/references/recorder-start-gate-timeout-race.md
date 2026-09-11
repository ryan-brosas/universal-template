<!-- capsule-v2 -->
# Start-gate timeout race — how do you start on a stream that may land during the failure tick itself?

**Source:** screenity GPL-3.0 `master@e10e375fafa1680de99ca6db36536dd4a1f4f7d4`; Codebase Memory `screenity`. **Question:** A user clicked record but the capture stream isn't ready — how do you defer without double-starting, and how do you avoid failing a stream that arrived inside the timeout window?

## Deferred start with race-aware timeout
**Path/Symbol:** `src/pages/Recorder/Recorder.jsx:1121-1241` (`getStreamReadiness`, `buildStreamDiagInfo`, `armStartGateTimeout`, `resetGateState`, `requestStart`, `tryStartIfReady`).
**Signature:** `requestStart()`; `armStartGateTimeout()` arms `START_GATE_TIMEOUT_MS` timer.
**Data Shape:** refs: `startRequested`, `startRequestedAt`, `isStarting`, `isRestarting` (+ `pendingStartAfterRestart`), `startGateTimeout`, `streamReadyAt`; readiness predicate over the live video track.

### Decisive source
```js
  function armStartGateTimeout() {
    clearStartGateTimeout();
    startGateTimeout.current = setTimeout(() => {
      if (!startRequested.current) return;
      const readiness = getStreamReadiness();
      if (readiness.ready) {
        // Stream arrived just before timeout.
        slLog("start-gate-timeout-race-ok");
        tryStartIfReady();
        return;
      }
      ... chrome.storage.local.set({ lastStreamCheckFail: diagInfo });
      resetGateState();
      sendRecordingError(chrome.i18n.getMessage("streamingDataTimeoutError"));
    }, START_GATE_TIMEOUT_MS);
  }

  function requestStart() {
    if (recorder.current !== null || isStarting.current) { /* bail-already-active */ return; }
    if (isRestarting.current) { pendingStartAfterRestart.current = true; return; }
    if (startRequested.current) { /* bail-already-requested */ return; }
    startRequested.current = true;
    ...
    const readiness = getStreamReadiness();
    if (readiness.ready) { startRecording(); } else { armStartGateTimeout(); }
  }
```
Readiness is deliberately minimal:
```js
  function getStreamReadiness() {
    if (!helperVideoStream.current) return { ready: false, reason: "stream-ref-null" };
    const vt = helperVideoStream.current.getVideoTracks();
    if (vt.length === 0) return { ready: false, reason: "zero-video-tracks" };
    if (vt[0].readyState !== "live") return { ready:false, reason:"track-not-live", trackState: vt[0].readyState };
    return { ready: true };
  }
```

**Flow:** requestStart dedups four ways (recorder exists / starting / restarting→queue / already requested) → immediate start when ready else arm gate → stream events call tryStartIfReady (no-op unless still requested) → at timeout, re-check readiness FIRST (race-ok path) before resetting gate state and surfacing the localized error with full diagnostics.
**Invariant:** a start request can produce at most one recorder; the timeout path must treat a just-arrived stream as success, not failure; failure diagnostics capture stream/track/visibility state (`buildStreamDiagInfo`) before reset so the log explains WHY it never became ready.
**Probe:** deterministic anchors: grep Recorder.jsx for `start-gate-timeout-race-ok` (:1158), `stream never became ready` (:1166), `requestStart-bail-already-active` (:1197). Byte-exact at HEAD.

## Get live surrounding code
**Retrieve:**
```
search_graph(project="screenity", name_pattern="^(armStartGateTimeout|clearStartGateTimeout|getStreamReadiness|requestStart|tryStartIfReady)$")
→ observed exactly these 5 functions at :1151/:1175/:1121/:1194/:1233 in screenity.src.pages.Recorder.Recorder.
```

## Verdict
Adopt the re-check-at-timeout pattern and the four-way request dedup. Adapt the readiness predicate to your stream source and the diagnostics payload to your logger. Omit i18n message keys.
