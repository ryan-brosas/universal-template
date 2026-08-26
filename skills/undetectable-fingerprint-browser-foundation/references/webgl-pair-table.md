<!-- capsule-v2 -->
# WebGL pair table — how do you fake GPU strings without contradicting capability tier?

**Source:** itbrowser-net/undetectable-fingerprint-browser no-LICENSE `main@6df77401149f82fa089589946859a92a0d9f6bb7`; Codebase Memory `undetectable-fingerprint-browser`. **Question:** When spoofing WEBGL_debug_renderer_info and context parameters, what keeps WebGL1/WebGL2 answers mutually consistent?

## Capability tier is part of GPU identity
**Path/Symbol:** `fingerprints/webgl.json`:2–27 (rows 1–2); graph Variables `fingerprints.webgl.*` (8 keys).
**Signature:** `Array<{Renderer, Vendor, Version, ShadingLanguage, UnmaskedVendor, UnmaskedRenderer, Version2, ShadingLanguage2}>` — 630 rows, fixed 8-key shape.
**Data Shape:** `Renderer`/`Vendor` are constant "WebKit WebGL"/"WebKit" on all 630 rows; all GPU identity lives in the Unmasked pair; 60 rows have `Version2:""` AND `ShadingLanguage2:""`.

### Decisive source
```json
{
    "Renderer": "WebKit WebGL",
    "ShadingLanguage": "WebGL GLSL ES 1.0 (OpenGL ES GLSL ES 1.0 Chromium)",
    "ShadingLanguage2": "",
    "UnmaskedRenderer": "ANGLE (Intel, Intel(R) HD Graphics 3000 Direct3D9Ex vs_3_0 ps_3_0, igdumd32.dll)",
    "UnmaskedVendor": "Google Inc. (Intel)",
    "Vendor": "WebKit",
    "Version": "WebGL 1.0 (OpenGL ES 2.0 Chromium)",
    "Version2": ""
}
```
Row 2 contrast (AMD D3D11): `"UnmaskedRenderer": "ANGLE (AMD, AMD Radeon(TM) Graphics (0x00001506) Direct3D11 vs_5_0 ps_5_0, D3D11)"` with populated `"ShadingLanguage2": "WebGL GLSL ES 3.00 ..."`, `"Version2": "WebGL 2.0 (OpenGL ES 3.0 Chromium)"`.
Executed probes: total=630; GL1-only (`Version2==""`) = 60; distinct UnmaskedVendors include bare "Google Inc.", PCI-ID forms "(0x344C5250)", and vendor parens AMD/Intel/Microsoft/NVIDIA/VMware/Google/Unknown.

**Flow:** choose a row → report masked `Vendor`/`Renderer`/`Version`/`ShadingLanguage` verbatim → report `UNMASKED_VENDOR_WEBGL`/`UNMASKED_RENDERER_WEBGL` from Unmasked* → if the row's GL2 fields are empty strings, the WebGL2 context itself must fail/be absent; else answer GL2 constants too.
**Invariant:** renderer-era coherence — Direct3D9Ex/vs_3_0-era ANGLE strings co-occur ONLY with empty GL2 fields; D3D11 vs_5_0 rows carry populated GL2 constants. A profile claiming an HD-3000-class GPU while exposing a WebGL2 context is a self-inflicted detection signal. Malformed real-world strings ("Graphics", "HD Graphics", 3 rows) are kept verbatim, not prettified.
**Probe:** `jq '[.[] | select(.Version2 == "" or .ShadingLanguage2 == "")] | length' fingerprints/webgl.json` → `60` pins the legacy cohort size (executed pass 1). No test runner exists at pin; this deterministic probe stands in.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "undetectable-fingerprint-browser", label: "Variable", file_pattern: "webgl.json", limit: 10 });
```

## Verdict
Adopt paired-row selection with empty-string GL2 markers for pre-WebGL2 GPUs and constant Chromium GL1 strings; adapt by joining this table to your injection layer's context-creation gate; omit inventing hybrid rows (e.g., D3D9Ex + WebGL2) or normalizing malformed captured strings.
