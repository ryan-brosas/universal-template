<!-- capsule-v2 -->
# Full profile schema — what is the anatomy of a complete multi-surface spoofing profile?

**Source:** itbrowser-net/undetectable-fingerprint-browser no-LICENSE `main@6df77401149f82fa089589946859a92a0d9f6bb7`; Codebase Memory `undetectable-fingerprint-browser`. **Question:** Which surfaces must one record cover so every fingerprinting API answers from the SAME identity?

## One record = every leakable surface, pre-coordinated
**Path/Symbol:** `fingerprints/fingerprints.db.xz` (xz JSON stream; field paths `.navigator`, `.screen`, `.plugins[]`, `.webgpu`, `.webgl`, `.webrtc`, `.audio`, `.css`, `.fonts`, `.keyboard`, `.codecs`, `.headers[]`). Graph coverage caveat: binary artifact, freshness "not_tracked" in index hash records — verified by direct stream probes only.
**Signature:** `Array<Profile>` (exactly **10,000** records at this pin) where Profile = `{hardware_concurrency, device_memory, do_not_track, hls_enabled, navigator, screen, plugins[], webgpu, webgl, webrtc, speech[], fonts[], keyboard{}, codecs[], css{}, headers[], audio{}}` — all 17 keys present on 10000/10000 records; heterogeneity lives inside planes (see profile-cohort-taxonomy), never at the top level.
**Data Shape (decompressed stream):** navigator carries UA-CH (`brands` major-only x3, `full_version_list` full versions x3, GREASE entry), ua-ch platform object `{name, version, architecture, model, bitness, wow64}`, and `user_agent` stored as integer index; the pack is WINDOWS-ONLY (platform.name "Windows" ×9998 + "" ×2 byte-duplicate anomaly records); css is a uniform 24-key media-feature vocabulary union (any-hover, any-pointer, aspect-ratio numeric, color-gamut:srgb …); screen has avail*/outer* with `outer_height: null` allowed; plugins = five PDF Viewer clones with hashed int ref/mimes; webgl mirrors webgl.json strings plus `extensions[]`/`extensions2[]` INDEX arrays and a properties map whose WebGL2 twins are the same key suffixed `2`; webrtc splits receiver/sender x video/audio codec+extension tables; audio is the complete WebAudio default-value map (sampleRate varies 44100/48000 across records).

### Decisive source
```jsonc
// fragments from decompressed fingerprints.db.xz stream (verbatim)
{"hardware_concurrency":4,"device_memory":8,"do_not_track":true,"hls_enabled":false,
 "navigator":{"user_agent":1,"app_version":"5.0 (Windows NT 10.0; Win64; x64) ... Chrome/117.0.0.0 Safari/537.36","vendor":"Google Inc.",
   "full_version":"117.0.5938.150",
   "brands":[{"brand":"Google Chrome","version":"117"},{"brand":"Not;A=Brand","version":"8"},{"brand":"Chromium","version":"117"}],
   "platform":{"name":"Windows","version":"10.0.0","architecture":"x86","model":"","bitness":"64","wow64":false}},
 "screen":{"avail_left":0,"avail_top":0,"avail_width":1920,"avail_height":1040,"width":1920,"height":1080,"outer_width":1920,"outer_height":null,"color_depth":24,"pixel_depth":24,"device_pixel_ratio":1},
 "webgl":{"unmasked_renderer":"ANGLE (NVIDIA, NVIDIA GeForce GTX 460 Direct3D11 vs_5_0 ps_5_0, D3D11)","extensions":[0,1,2],"properties":{"maxTextureSize":"16384"}}}
```
(Third fragment elides long index arrays; full values verified in-stream during pass-1 probes.)

**Flow:** resolve indexes to concrete vocabularies → inject navigator/screen/plugin planes → configure webgpu limit maps per performance tier → gate webgl/webrtc answers from the same record's tables → apply audio/css/font/keyboard maps so AudioContext, media queries, font probing, and KeyboardEvent codes all agree.
**Invariant:** cross-surface coherence is the product's core claim ("Consistency Analysis Engine", README l.41): Windows UA-CH platform ⇔ Win32-ish UA ⇔ x86/64-bit/wow64:false ⇔ D3D11 ANGLE string ⇔ 1920x1080 desktop screen ⇔ aligned brand majors. Any single-surface randomizer breaks at least one join a detector can probe.
**Probe:** `xz -dc fingerprints/fingerprints.db.xz | jq 'length'` → `10000` (record count, executed pass 2); and `xz -dc fingerprints/fingerprints.db.xz | strings -n 8 | grep -o '"hardware_concurrency":[0-9]*' | head -2` → non-empty output pins the top-level knob surface (executed pass 1).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.check_index_coverage({ project: "undetectable-fingerprint-browser", paths: ["fingerprints/fingerprints.db.xz"] });
```

## Verdict
Adopt the surface checklist (it is effectively the threat-model enumeration of browser fingerprinting) and the single-record-per-identity rule; adapt storage layout and field names; omit treating any surface as optional — the schema's point is that ALL of them ship together. Caveats: no runner exists to execute profiles (binary-only product); db.xz not graph-tracked, evidence is direct-stream only.
