---
name: undetectable-fingerprint-browser-foundation
description: "Use when porting browser-fingerprint spoofing datasets, building a fingerprint-profile generator or consistency checker, fabricating UA-CH brand headers, integrating automation frameworks with a patched Chromium via startup parameters, or weighting device-profile sampling to mimic real-world traffic. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval."
---
# Undetectable Fingerprint Browser: anti-detection data-contract foundation

## Use this for
Use when porting browser-fingerprint spoofing datasets, building a fingerprint-profile generator or
consistency checker, fabricating UA-CH brand headers, integrating automation frameworks with a
patched Chromium via startup parameters, or weighting device-profile sampling to mimic real-world
traffic. Source code and direct tests are ground truth; references carry decisive excerpts and graph
retrieval.

## Load the matching source dump
- `references/launch-contract.md` — how do you attach Puppeteer/Playwright/CDP automation to a fingerprint-spoofed Chromium with zero client code?
- `references/ua-profile-record.md` — what fields make ONE coherent UA/device profile record, and which fields are engine-conditional?
- `references/weighted-profile-sampling.md` — how are profiles selected so synthetic traffic matches real-world device distribution?
- `references/webgl-pair-table.md` — how do you fake GPU strings without contradicting WebGL1/WebGL2 capability tier?
- `references/fingerprint-db-schema.md` — what is the full anatomy of a complete multi-surface spoofing profile?
- `references/index-indirection.md` — why are fonts/headers/codecs/user_agent stored as integer indexes and how must a porter resolve them?
- `references/grease-brand-list.md` — how do you fabricate Sec-CH-UA brands / full_version_list lists that survive UA-CH checks?
- `references/webrtc-plane.md` — what shape must WebRTC codec/extension answer tables take, and which captured quirks would betray a naive reimplementation?
- `references/webgpu-limits-plane.md` — how do you fake navigator.gpu adapter info/limits coherently per performance tier?
- `references/profile-cohort-taxonomy.md` — how must a profile-database loader branch on record cohorts before injecting anything?
- `references/webaudio-default-map.md` — which AudioContext parameters vary, which are Nyquist-derived from sample rate, and what must stay byte-stable?
- `references/plugins-taxonomy.md` — how do the four plugin cohorts and their name-keyed ref-hash constants survive plugin enumeration?
- `references/screen-geometry-cohorts.md` — which screen geometries, dpr floats, and outer-dimension quirks are real-captured versus synthetic tells?
- `references/speech-voice-defaults.md` — how must speechSynthesis voices be populated with at-most-one locale-coherent default?
- `references/vocab-order-planes.md` — which header/codecs/keyboard vocabularies carry per-profile data versus frozen pack constants?
- `references/css-media-values.md` — which css media features gate per Chromium generation, and which values are exact derivations of dims/dpr?
- `references/webgl-db-interior.md` — how do three properties-map shapes signal WebGL2 capability tier independent of renderer vintage?
- `references/fonts-length-spectrum.md` — how many fonts may an identity claim so font-probe detectors see a real Windows install?
- `references/navigator-scalar-cohorts.md` — which navigator scalars are frozen shims, and where do version-alignment laws actually break?
- `references/top-knob-ladders.md` — what value ladders and couplings constrain hardware_concurrency/device_memory/do_not_track/hls_enabled?

## Capsule map
- **Launch contract** — `launch-contract`: patched Chromium consumes `--itbrowser=<profile.json>`; per-profile `--user-data-dir`, process-level `--proxy-server`, CDP via `--remote-debugging-port`; frameworks swap only executablePath.
- **UA profile record** — `ua-profile-record`: 14-field record; `connection` optional (4118/10000), `oscpu`+empty `vendor` gate together on Gecko.
- **Weighted sampling** — `weighted-profile-sampling`: `weight` sums to exactly 1.0 over 10000 records ⇒ probability mass; sample cumulatively, never uniformly.
- **WebGL pair table** — `webgl-pair-table`: 630 rows pair GL1 constants with `*2` GL2 fields; 60 legacy rows carry EMPTY-STRING GL2 — capability tier is part of GPU identity.
- **Full profile schema** — `fingerprint-db-schema`: one record covers navigator (UA-CH + platform), screen, plugins, webgpu limits, webgl (+properties map), webrtc codec tables, audio defaults, css media features, fonts/keyboard/codecs.
- **Index indirection** — `index-indirection`: cross-record vocabularies stored as integer indexes for dedupe/compression (163x); resolvers ship with the binary, not this repo.
- **GREASE brand list** — `grease-brand-list`: 3-entry brands vs full_version_list with "Not;A=Brand" v8 at fixed position; major-only vs full versions aligned to UA major.
- **WebRTC plane** — `webrtc-plane`: three capture generations (99 rich SDP lists / 9865 compact indexed-mimeType objects / 36 empty); rich audio slot duplicates the VIDEO codec list byte-for-byte.
- **WebGPU limits plane** — `webgpu-limits-plane`: 5-key gate map; standard 31-key GPUSupportedLimits; low==high tier on 9998/10000; trailing-space `"limits_gpudevice "` string-valued twin; bgra8unorm default.
- **Profile cohort taxonomy** — `profile-cohort-taxonomy`: 10,000 records, 17 uniform top-level keys, Windows-only pack, six webrtc×webgpu cohorts — load-then-classify, never one-shape parsing.
- **WebAudio default map** — `webaudio-default-map`: 108-key map collapsing to 31 distinct bodies; four free knobs (9-value sample-rate ladder), Nyquist trio ≡ ±sr/2 on ALL records, one float32 compressor-ratio anomaly.
- **Plugins taxonomy** — `plugins-taxonomy`: canonical5 ×9410 / empty ×55 / NaCl ×59 / tail ×476 over 358 signatures; ref quintet byte-stable ⇒ name-keyed hash; Flash dup-name cohort ×3.
- **Screen geometry cohorts** — `screen-geometry-cohorts`: 664 (w,h,dpr) clusters headed by real Windows geometry; 96 noisy float32 dprs; depth twins always equal; outer_height NULL ×10000 while outer_width populated.
- **Speech voice defaults** — `speech-voice-defaults`: lengths 0..339; exactly-one-default ×9871 vs no-default ×129; default is local_service=true ×9657 and locale-coherent.
- **Vocab order planes** — `vocab-order-planes`: header order = data (62 orderings over lens 31..37); codecs frozen [0..5] ×10000; keyboard empty-cohort ×492 is itself a signature.
- **CSS media values** — `css-media-values`: presence-gated keyset tracks Chromium generation (update ×9432, reduced-transparency ×2824); aspect-ratio ≡ dims·10⁴ and resolution ≡ dpr·96 exactly.
- **WebGL db interior** — `webgl-db-interior`: properties takes THREE shapes ({157,92twins}×9749 / {63}×190 / {65}×61); tier = keyset shape not renderer vintage; legacy extensions2 ≡ [[43]]; string-serialized maxTextureSize ladder.
- **Fonts length spectrum** — `fonts-length-spectrum`: 10..1518 with 495 distinct lengths, modes 201×1186 / 381×624 — a real install-count spectrum, not a band.
- **Navigator scalar cohorts** — `navigator-scalar-cohorts`: six frozen shims ×10000; UA-string rich only ×99 (alignment laws scoped); corpus-wide brand↔full_version has exactly 10 drift records; anomaly twins carry empty brands + empty full_version.
- **Top knob ladders** — `top-knob-ladders`: hardware_concurrency 34 distinct values mode 12×2332; device_memory spec-capped ≤8 (8×9089); dnt {false:8571,true:1429}; hls_enabled CONSTANT false; hc×dm coupling.

## Extending the foundation
Add one `references/<seam>.md` capsule for one graph-selected, source-confirmed porting question.
Add one matching loader line and map entry; keep evidence in the capsule, not this leaf.

## Provenance
itbrowser-net/undetectable-fingerprint-browser (**no LICENSE file at pin** — README legal disclaimer
only; reuse citations-only), `main@6df77401149f82fa089589946859a92a0d9f6bb7`; Codebase Memory project
`undetectable-fingerprint-browser` (FULL mode, generation 2026-08-23T00:13:38Z, ready, 66 nodes /
65 edges, parse_partial=0, skipped=0; pin re-verified 2026-08-26 via index_status head==base==checkout
HEAD and git fetch showing zero new upstream commits). Pass 1 delivered 7 capsules (launch/data-contract
planes); pass 2 deepened the db.xz census plane (+3 capsule-v2, 2 refactors: webrtc-plane,
webgpu-limits-plane, profile-cohort-taxonomy); pass 3 mined audio/plugins/screen/speech/vocabulary
planes (+5, +1 schema refactor); pass 4 mined css/webgl-interior/fonts/navigator-scalar/top-knob
value planes (+5, schema refactor incl. css uniformity refutation) — closing every one of the 17
db.xz top-level keys; pass 7 RESTORED the ten pass-3/4 capsule files after an external reset of the
leaf to its pass-2 snapshot (all Data Shape numbers re-grounded by fresh executed probes at the same
pin; navigator alignment-law scope refined: UA-string rich cohort ×99, corpus-wide brand↔full_version
drift exactly ×10). Caveats: `fingerprints/fingerprints.db.xz` is not tracked by
graph hash records (verified from direct stream probes); db-only key surfaces are NOT graph nodes
(BM25 totals 0); `usage/*.png` excluded by design; repo has no executable code or test runner at pin.

## Full view (memory graph)
Revalidate `undetectable-fingerprint-browser` before porting: run `index_status`,
`check_index_coverage`, `search_graph`, `trace_path`, and `get_code_snippet`. Record the graph root,
branch, commit, mode, node/edge counts, freshness, and any coverage caveats; source and direct tests
decide shipped claims. The graph's 27 Variable nodes enumerate the exact JSON key surface of
user-agents.json (19) and webgl.json (8).

## Boundaries
Adopt the data contracts (record schemas, weight semantics, capability-tier pairing, GREASE list
shape, launch flags) and the verbatim-real-capture doctrine. Adapt the injection mechanism: the
Chromium patches and Consistency Analysis Engine are binary-only at this pin, so re-implement
injection natively. Omit redistribution of dataset contents (unlicensed) and any claim about the
product's closed-source internals.
