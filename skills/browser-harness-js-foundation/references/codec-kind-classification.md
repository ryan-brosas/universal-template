<!-- capsule-v2 -->
# Codec-Kind Classification — container mime lies, the codecs= parameter is truth

## Source
Repo: browser-harness-js @ main`6b18940` (unchanged vs base_sha).

## Question
How must an MSE-capture tool classify a SourceBuffer as audio vs video, and what breaks if it uses the obvious check?

## Path / Symbol
`skills/ttdl/scripts/ttdl` hook :172-190 (AUDIO/VIDEO fourcc tables + classification), contrast comment :165-171; ytdl's simpler `mime.startsWith` version at ytdl hook :141-146.

## Signature
```js
// TikTok puts the AUDIO in a SourceBuffer whose CONTAINER is video/mp4 —
// only the codecs= parameter ("mp4a.*") reveals it's audio. A naive
// mime.startsWith("video") check (the ytdl pattern) mis-tags the audio buffer
// as video and you end up with a SILENT capture.
const codec = (mime.match(/codecs="([^"]+)"/)||[])[1] || '';
const base  = codec.split('.')[0].toLowerCase();      // avc1.64001e → avc1
const AUDIO = ["mp4a","opus","ac-3","ac3","ec-3","ec3","dtsc","dtsl","samr","sawp","enca","mha1","mhm1"];
const VIDEO = ["avc1","avc3","hvc1","hev1","hvc3","hev3","av01","vp08","vp09","vp8","vp9","encv"];
const kind = AUDIO.includes(base) ? "audio"
           : VIDEO.includes(base) ? "video"
           : (mime.startsWith("audio") ? "audio"     // fallback only when codec unknown
           : mime.startsWith("video") ? "video" : "other");
```

## Data Shape
Classification feeds `{kind, codec}` on each buffer entry; downstream "largest of each kind" selection and the ffmpeg mux input order depend on kind being right.

## Decisive source
ttdl :165-171 block comment quoted in Signature above (TIKTOK-SPECIFIC note). ttdl :489-491 documents why ffmpeg is always required for TikTok: "TikTok serves audio and video as SEPARATE SourceBuffers" (no muxed single-buffer path like YouTube sometimes gives). The fourcc lists cover the ISO-BMFF sample-entry prefixes (avc1/hvc1/mp4a/opus/ec-3/dtsc…) plus WebKit/VP9 variants — porters should extend rather than trim them.

## Flow / Invariant
Classify by registered codec fourcc FIRST; container mime prefix only as last-resort fallback for unlisted codecs. A silent output file is the symptom of getting this wrong — video-only mux with the audio stream dropped by kind mis-sort.

## Probe (direct tests)
LIVE this pass: appended `'video/mp4; codecs="avc1.64001e"'` through the ttdl-style classifier → entry classified `{"kind":"video","codec":"avc1.64001e",bytes:991017}` (probe transcript in work record). Deterministic probe at pin: `grep -c '"mp4a"' skills/ttdl/scripts/ttdl` → 1 (table present); `grep -c 'mime.startsWith' skills/ytdl/scripts/ytdl` → 1 (:157, one line carrying both video and audio branches) — ERRATUM pass-4 audit: shipped as "≥2", live count at pin is 1; the weaker single-line pattern is what ytdl gets away with because YouTube pairs containers honestly.

## Retrieve
grep-first (`codecs=`, `AUDIO`, `fourcc`).

## Verdict
ADOPT the codec-first ladder verbatim (including both fourcc tables) for any MSE capture targeting TikTok or any site that muxes audio into video-container SourceBuffers.
