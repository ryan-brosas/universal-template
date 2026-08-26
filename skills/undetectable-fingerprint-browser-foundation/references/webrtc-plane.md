<!-- capsule-v2 -->
# WebRTC plane — how do you reconstruct a codec/extension answer surface that matches the rest of the identity?

**Source:** itbrowser-net/undetectable-fingerprint-browser no-LICENSE `main@6df77401149f82fa089589946859a92a0d9f6bb7`; Codebase Memory `undetectable-fingerprint-browser`. **Question:** When spoofing `RTCRtpReceiver.getCapabilities`/SDP answers, what shape must the codec and header-extension tables take, and which dataset quirks would betray a naive reimplementation?

## Three capture generations inside one corpus
**Path/Symbol:** `fingerprints/fingerprints.db.xz` stream fields `.webrtc.{receiver,sender}.{video,audio}.{codecs,extensions}` (census over all 10,000 records). Graph coverage caveat: binary artifact, freshness "not_tracked" — direct-stream evidence only; db keys are NOT graph nodes (BM25 totals 0).
**Signature:** `webrtc = {receiver: {video: Slot, audio: Slot}, sender: {video: Slot, audio: Slot}}` where `Slot = RichCodec[] | CompactCodec | {}` and `RichCodec = {clockRate: 90000, mimeType: string, sdpFmtpLine?: string}`, `CompactCodec = {clockRate, mimeType: INDEX_INT, sdpFmtpLine?, channels?}`.
**Data Shape (full-stream census):** RICH ×99 (four codec-list signatures n=1/76/18/4 + 4-entry named extension arrays), COMPACT ×9865 (`receiver.video` → `{clockRate:90000, mimeType:13, sdpFmtpLine:"repair-window=10000000"}`; `receiver.audio` → `{channels:1, clockRate:8000, mimeType:20, sdpFmtpLine:"111/111"}`; extensions → `{"direction":"sendrecv","uri":10}` with indexed uri), EMPTY ×36 (`{}` in all slots).

### Decisive source
```jsonc
// fragments from decompressed fingerprints.db.xz stream (verbatim)
// COMPACT form (9865/10000 records) — mimeType and uri are INTEGER INDEXES:
{"clockRate":90000,"mimeType":13,"sdpFmtpLine":"repair-window=10000000"}          // receiver.video
{"channels":1,"clockRate":8000,"mimeType":20,"sdpFmtpLine":"111/111"}             // receiver.audio
{"direction":"sendrecv","uri":10}                                                  // *.extensions
// RICH form (99/10000 records) — inline strings, full SDP list; audio slot == video slot BYTE-FOR-BYTE:
[{"clockRate":90000,"mimeType":"video/VP8"},{"clockRate":90000,"mimeType":"video/rtx"},
 {"clockRate":90000,"mimeType":"video/VP9","sdpFmtpLine":"profile-id=0"}, ...
 {"clockRate":90000,"mimeType":"video/H264","sdpFmtpLine":"level-asymmetry-allowed=1;packetization-mode=1;profile-level-id=f4001f"},
 {"clockRate":90000,"mimeType":"video/AV1","sdpFmtpLine":"profile=1"},
 {"clockRate":90000,"mimeType":"video/red"},{"clockRate":90000,"mimeType":"video/ulpfec"},
 {"clockRate":90000,"mimeType":"video/flexfec-03","sdpFmtpLine":"repair-window=10000000"}]
```
Rich-signature deltas: H264 profile-level-id sets 42001f/42e01f/4d001f ± f4001f ± 64001f, VP9
profile-id=3 presence, AV1 profile=1 presence. Rich extensions (all four slots): ssrc-audio-level,
abs-send-time, transport-wide-cc-extensions-01, sdes:mid — all `"sendrecv"`.

**Flow:** pick the record's cohort first → rich: inject the full ordered SDP list verbatim per slot; compact: resolve mimeType/uri indexes against the product's private vocabulary BEFORE answering getCapabilities; empty: the profile intends no webrtc masking.
**Invariant:** the audio slot of every rich record duplicates the VIDEO codec list byte-for-byte — that duplication is IN the captured data, so a porter who "fixes" it into a plausible audio list (opus/PCMU...) produces an identity NO real capture ever had. Conversely the compact audio object is genuinely audio-shaped ({channels:1, clockRate:8000}).
**Probe:** `xz -dc fingerprints/fingerprints.db.xz | jq -c '[.[] | .webrtc.receiver.video.codecs | tostring] | group_by(.) | map({n: length})'` → exactly ten groups: [1,76,4,18,9865,36]-shaped distribution pinning rich/compact/empty counts (executed pass 2).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "undetectable-fingerprint-browser", query: "webrtc codecs extensions receiver sender mimeType", label: "Variable", limit: 10 });
```
(total 0 at pin — proves the webrtc plane lives ONLY in the untracked binary artifact; absence of irrelevant graph loading.)

## Verdict
Adopt the three-cohort model and the exact compact-form field shapes (indexed mimeType/uri, clockRates 90000 video / 8000 audio); adapt by building your own mimeType/uri vocabulary tables when regenerating profiles; omit any assumption that rich-record audio slots are audio codecs — preserve captured quirks verbatim if fidelity to this corpus matters, and document them as known data-quality traps otherwise. Caveat: db.xz not graph-tracked; census evidence is direct-stream only.
