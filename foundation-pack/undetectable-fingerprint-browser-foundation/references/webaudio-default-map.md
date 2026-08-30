<!-- capsule-v2 -->
# WebAudio default map — four free knobs, a Nyquist-derived trio, and one anomalous record

**Source:** itbrowser-net/undetectable-fingerprint-browser no-LICENSE `main@6df77401149f82fa089589946859a92a0d9f6bb7`; Codebase Memory `undetectable-fingerprint-browser`. **Question:** Which AudioContext parameters must a profile generator emit so `new AudioContext()` and offline probes agree with the rest of the identity?

## Path/Symbol
**Path/Symbol:** `fingerprints/fingerprints.db.xz` → `.audio` (flat map, 108 keys, keyset uniform on all 10,000 records). Graph coverage caveat: binary artifact is freshness `not_tracked` in index hash records — every claim below was verified by direct stream probes (`xz -dc | jq`), and BM25 retrieval for this plane returns total 0 (see Retrieve).

## Signature
**Signature:** `.audio` = `Record<WebAudioParamName, number | null>`; the corpus collapses to exactly **31 distinct maps**. Deleting the FOUR free-varying knobs leaves only **10 distinct bodies** — i.e., virtually all entropy lives in four knobs plus their derived consequences.

## Data Shape
- `BaseAudioContextSampleRate` — nine values, far from binary: `{48000×8417, 44100×1394, 96000×87, 192000×72, 384000×13, 16000×12, 8000×3, 32000×1, 88200×1}`.
- `AudioContextBaseLatency` — eight values; dominant `0.01×9302`; every other value is an integer-hardware-quantum quotient of the SAME record's sample rate: `512/48000=0.010666666666666666 ×462`, `448/44100=0.010158730158730159 ×224`, `256/48000=0.005333333333333333 ×2`, plain `0.012 ×7`, `512/88200=0.005804988662131519 ×1`, `444/44100=0.010068027210884354 ×1`, `608/48000=0.012666666666666666 ×1`.
- `AudioContextOutputLatency` — `{null×1, 0×9998, 0.032×1}`.
- `AudioDestinationNodeMaxChannelCount` — `{2×9643, 8×246, 6×59, 4×38, 1×14}`.
- THREE Nyquist-derived keys: `BiquadFilterNodeFrequencyMaxValue == OscillatorNodeFrequencyMaxValue == +sampleRate/2` and `OscillatorNodeFrequencyMinValue == −sampleRate/2` on ALL 10,000 records (their value ladders mirror the sample-rate ladder count-for-count).
- ONE anomalous record carries float32-drift offsets on the compressor-ratio trio at sample rate 44100: `DynamicsCompressorNodeRatio{Default,Max,Min}Value = 12.084571838378906 / 20.084571838378906 / 1.0845723152160645` vs `12/20/1` on the other 9,999.
- Remaining ~98 keys are byte-stable spec constants — including FLOAT32_MAX serialized .NET-style as `3.4028234663852886E+38`, `DynamicsCompressorNodeReduction ≡ 0`, Attack default `0.003000000026077032` (float32 noise), `BiquadFilterNodeGainMaxValue 1541.273681640625`.

### Decisive source
```jsonc
// fresh pass-7 stream probes (verbatim jq outputs) against fingerprints.db.xz @ pin
sr ladder   : [{"v":8000,"n":3},{"v":16000,"n":12},{"v":32000,"n":1},{"v":44100,"n":1394},
               {"v":48000,"n":8417},{"v":88200,"n":1},{"v":96000,"n":87},{"v":192000,"n":72},{"v":384000,"n":13}]
nyquist bad : 0                      // BiquadFilterNodeFrequencyMaxValue != sr/2 count
maps        : 31                     // [.[].audio] | unique | length
del4 bodies : 10                     // delete the four free knobs -> residual distinct bodies
anomaly     : [{"d":12.084571838378906,"m":20.084571838378906,
                "i":1.0845723152160645,"sr":44100}]
```

**Flow:** pick the record first (weighted sampling) → read its `.audio` map verbatim → derive nothing locally except what the record already encodes → inject as AudioContext defaults so `sampleRate`, `baseLatency`, `destination.maxChannelCount`, oscillator/biquad ranges, and DynamicsCompressor ratios all answer from ONE captured identity.
**Invariant:** the Nyquist trio is DERIVED — never randomize `OscillatorNode/BiquadFilterNode` frequency bounds independently of `BaseAudioContextSampleRate`; a mismatched pair (e.g., sr 48000 with max 11025) is a synthetic tell no real browser produces. Do not normalize the `.E+38` float literal or float32 noise values — real captures serialize them that way. The compressor-ratio anomaly record proves the pack tolerates capture noise; do not "fix" it away when replaying.

**Probe:** `xz -dc fingerprints/fingerprints.db.xz | jq -c '[.[].audio.BaseAudioContextSampleRate] | group_by(.) | map({v:.[0],n:length})'` → the nine-value ladder above (executed pass 7); and `xz -dc fingerprints/fingerprints.db.xz | jq -c '[.[] | select(.audio.BiquadFilterNodeFrequencyMaxValue != (.audio.BaseAudioContextSampleRate)/2)] | length'` → `0` (executed pass 7).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "undetectable-fingerprint-browser",
  query: "WebAudio AudioContext sample rate base latency oscillator Nyquist biquad frequency max" });
// executed pass 7 -> total: 0 (plane absent from node surface; this capsule is the only path)
```

## Verdict
Adopt the four-knob + derived-trio value model and the verbatim-constant body; adapt storage (any KV works — the plane is flat); omit per-key randomization of spec constants. Caveats: evidence is direct-stream only (artifact not graph-tracked); no runner exists to execute an AudioContext against the injected profile.
