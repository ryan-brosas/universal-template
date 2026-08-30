<!-- capsule-v2 -->
# Profile cohort taxonomy — how do you consume a heterogeneous captured-profile database without assuming one shape?

**Source:** itbrowser-net/undetectable-fingerprint-browser no-LICENSE `main@6df77401149f82fa089589946859a92a0d9f6bb7`; Codebase Memory `undetectable-fingerprint-browser`. **Question:** What must a profile-database loader branch on before injecting any single record?

## One OS, 17 uniform keys, six behavioral cohorts
**Path/Symbol:** `fingerprints/fingerprints.db.xz` stream: top-level `Array<Profile>` (10,000 records) and cross-field cohorts `.webrtc.receiver.video.codecs|type` × `.webgpu.enabled` × `.webgpu.high_performance.limits != null`. Graph coverage caveat: binary artifact, freshness "not_tracked" — direct-stream evidence only.
**Signature:** top-level keys are uniform — exactly 17 present on 10000/10000 records: audio, codecs, css, device_memory, do_not_track, fonts, hardware_concurrency, headers, hls_enabled, keyboard, navigator, plugins, screen, speech, webgl, webgpu, webrtc. Heterogeneity lives INSIDE planes, not at the top level.
**Data Shape (full-stream census):** navigator.platform.name = "Windows" ×9998 + "" ×2; the two anomalies are byte-duplicate records (`ua_idx 108`, `brands: null`, Windows NT app_version, screen 1920). UA indexes span 0..219 with 102 distinct values used. Cross-tab of webrtc richness × webgpu state yields SIX cohorts:

| rich_webrtc | wg_enabled | limits_present | n |
|---|---|---|---|
| false | false | false | 574 |
| false | true | false | 1504 |
| false | true | true | 7823 |
| true | true | true | 74 |
| true | true | false | 19 |
| true | false | false | 6 |

**Decisive source**
```jsonc
// census outputs (verbatim jq group_by results, pass 2)
[{"p":"Windows","n":9998},{"p":"","n":2}]                       // platform distribution
[{"cohort":{"rich_webrtc":false,"wg_enabled":false,"limits_present":false},"n":574},
 {"cohort":{"rich_webrtc":false,"wg_enabled":true,"limits_present":false},"n":1504},
 {"cohort":{"rich_webrtc":false,"wg_enabled":true,"limits_present":true},"n":7823},
 {"cohort":{"rich_webrtc":true,"wg_enabled":true,"limits_present":true},"n":74},
 {"cohort":{"rich_webrtc":true,"wg_enabled":true,"limits_present":false},"n":19},
 {"cohort":{"rich_webrtc":true,"wg_enabled":false,"limits_present":false},"n":6}]
```

**Flow:** parse all 17 keys unconditionally → classify the record into its cohort (webrtc rich/compact/empty × webgpu enabled/disabled/limits-absent) → run the plane resolver for THAT cohort → never fall back to "default plausible values" for absent sub-shapes.
**Invariant:** cohorts correlate but are NOT deterministic — 6 records pair rich webrtc tables with a disabled webgpu plane, and the limits-absent cohort (2103) strictly exceeds the disabled cohort (580+12 fallback). Feature presence in one plane never implies presence in another; only the top-level 17-key set is invariant.
**Probe:** `xz -dc fingerprints/fingerprints.db.xz | jq 'length'` → `10000` exactly; and `[.[] | keys[]] | unique | length` → `17` (both executed pass 2).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "undetectable-fingerprint-browser", label: "File", limit: 10 });
```
→ total 4 (README.md, README_zh.md, user-agents.json, webgl.json): the db corpus itself is outside the graph index; File-label retrieval pins the repo's full indexed surface so a porter does not hunt for db-side graph nodes.

## Verdict
Adopt the load-then-classify discipline and the 17-key uniform contract; adapt cohort thresholds to your own regenerated corpus (these counts describe THIS capture); omit any single-shape parser or any assumption that the pack covers non-Windows platforms — it is a Windows-only pack, and multi-OS support must come from other sources. Caveat: db.xz not graph-tracked; census evidence is direct-stream only.
