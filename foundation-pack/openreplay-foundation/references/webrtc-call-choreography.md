<!-- capsule-v2 -->
# WebRTC call offer/answer with buffered ICE — how does an inbound agent call get user consent without losing candidates?

**Source:** openreplay AGPL-3.0 (tracker MIT) `main@99eb600`; Codebase Memory `openreplay`. **Question:** What ordering of confirm-UI, peer connection, local stream and ICE candidates avoids both dead calls and pre-answer leaks?

## Confirm first; buffer ICE until remote description set
**Path/Symbol:** `tracker/tracker-assist/src/Assist.ts` — socket.io dial config (:422–445: `reconnectionAttempts:30`, `randomizationFactor:0.5`, path `/ws-assist/socket`), `handleIncomingCallOffer` (:846–968), `renegotiateConnection` (:830–844), 30 s ring timeout (:870–875), canvas streams gate (:1033–1060), `session_calling_peer_key` list.
**Signature:** `handleIncomingCallOffer(from: string, offer: RTCSessionDescriptionInit)`.
**Data Shape:** signaling events `webrtc_call_offer|webrtc_call_answer|webrtc_call_ice_candidate|videofeed`; per-peer `Map<string, RTCPeerConnection>` (`this.calls`); ICE candidate buffer keyed by from.

### Decisive source
```ts
if (callingPeerIds.includes(from) || this.callingState === CallingState.True) {
  confirmAnswer = Promise.resolve(true)          // repeat caller auto-connects
} else {
  this.setCallingState(CallingState.Requesting)
  confirmAnswer = requestCallConfirm()           // UI + sound
  setTimeout(() => { if (this.callingState === CallingState.Requesting) initiateCallEnd() }, 30000)
}
...
await pc.setRemoteDescription(new RTCSessionDescription(offer))
const answer = await pc.createAnswer()
await pc.setLocalDescription(answer)
socket.emit('webrtc_call_answer', { from, answer })
this.applyBufferedIceCandidates(from)            // only AFTER answer is set
```

**Flow:** offer → already-calling? skip UI : show confirm (30 s ring timeout auto-end) → on accept create RTCPeerConnection(iceServers from server config) → request mic (`RequestLocalStream`: audio-only first, video toggled later) → SRD/ALD/answer → flush buffered candidates → remote stream attaches to call window after first user interaction (autoplay policy). Canvas annotation streams ride separate peer connections gated by `canSendMessages`.
**Invariant:** Candidates arriving before the answer MUST be queued (`applyBufferedIceCandidates` runs post-setLocalDescription). Denial must tear down before any media permission is requested.
**Probe:** `grep -c 'webrtc_call_ice_candidate' tracker/tracker-assist/src/Assist.ts` → `3`; `grep -c 'applyBufferedIceCandidates' tracker/tracker-assist/src/Assist.ts` → `3`; `grep -c 'session_calling_peer_key' tracker/tracker-assist/src/Assist.ts` → `5`.
**Coverage:** clean.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openreplay", query: "handleIncomingCallOffer webrtc_call_answer ice", limit: 10 });
```

## Verdict
Adopt buffer-until-answer + confirm-before-permission. Adapt signaling transport. Omit canvas peers if no annotation feature.
