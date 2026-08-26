<!-- capsule-v2 -->
# WebGPU limits plane — how do you fake `navigator.gpu` adapter info and limits coherently per performance tier?

**Source:** itbrowser-net/undetectable-fingerprint-browser no-LICENSE `main@6df77401149f82fa089589946859a92a0d9f6bb7`; Codebase Memory `undetectable-fingerprint-browser`. **Question:** When a porting host must answer `requestAdapter()`/`adapter.limits`/`adapter.info` from a synthetic profile, what does a captured, detector-safe webgpu record look like?

## One 5-key gate map with twin serialization inside
**Path/Symbol:** `fingerprints/fingerprints.db.xz` stream fields `.webgpu.{enabled,fallback,high_performance,low_performance,preferred_canvas_format}` and `.webgpu.high_performance.{features,info,is_fallback_adapter,limits,"limits_gpudevice "}` (census over all 10,000 records). Graph coverage caveat: binary artifact, freshness "not_tracked" — direct-stream evidence only.
**Signature:** `webgpu = {enabled: bool, fallback: bool|null, high_performance: Tier|null, low_performance: Tier|null, preferred_canvas_format: "bgra8unorm"|null}` where `Tier = {features: string[], info: AdapterInfo, is_fallback_adapter: bool, limits: GPUSupportedLimits, "limits_gpudevice ": StringValuedLimits}`.
**Data Shape (full-stream census):** enabled true ×9408 / false ×580 / true+fallback:true ×12; preferred_canvas_format "bgra8unorm" ×9419 / null ×581; low_performance == high_performance (deep-equal) on 9998/10000 records — the two tiers are captured identical, not differentiated; maxTextureDimension2D = 8192 ×7897 / limits-absent ×2103; info has 26 distinct real adapter strings; features has 10 distinct sets.

### Decisive source
```jsonc
// fragment from decompressed fingerprints.db.xz stream (verbatim)
"high_performance": {
  "limits": {"maxBindGroups":8,"maxBindingsPerBindGroup":1000,"maxBufferSize":...,
             "maxTextureDimension1D":8192,"maxTextureDimension2D":8192,
             "maxTextureDimension3D":2048,"maxTextureArrayLayers":256, ...},   // numeric values
  "limits_gpudevice ": {"maxTextureDimension1D":"8192","maxTextureDimension2D":"8192",
             "maxTextureDimension3D":"2048","maxTextureArrayLayers":"256", ...} // STRING values + trailing space
}
```
`limits` carries exactly the standard 31-key GPUSupportedLimits surface — there is NO
`maxTextureSize` key anywhere in the webgpu plane (that limit belongs to WebGL; the db's WebGL
`properties` map is where it lives). `"limits_gpudevice "` duplicates the same limits with every
value serialized as a string, under a key whose name ends in a space.

**Flow:** read `.webgpu.enabled` → if false/null-format cohort, answer as a WebGPU-less browser → else serve `info`/`features`/`limits` from high_performance verbatim and mirror them for low_performance → use preferred_canvas_format for canvas configuration defaults.
**Invariant:** tier symmetry — low and high performance maps are byte-identical in 9998/10000 records; a porter who synthesizes DIFFERENT low/high tiers invents a distribution the corpus never observed. And the trailing-space `"limits_gpudevice "` key must survive round-tripping byte-exactly or strict consumers re-serializing the profile will silently drop it.
**Probe:** `xz -dc fingerprints/fingerprints.db.xz | jq -c '{pcf: ([.[] | .webgpu.preferred_canvas_format] | group_by(.) | map({v: .[0], n: length})), lpm: ([.[] | .webgpu.low_performance == .webgpu.high_performance] | group_by(.) | map({same: .[0], n: length}))}'` → pcf [bgra8unorm ×9419, null ×581]; same [false ×2, true ×9998] (executed pass 2).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "undetectable-fingerprint-browser", query: "webgpu high_performance low_performance limits", limit: 10 });
```
(total 0 at pin — the entire webgpu plane lives ONLY in the untracked binary artifact.)

## Verdict
Adopt the 5-key gate map, the standard-limits surface (31 keys, numeric), and the bgra8unorm default; adapt tier handling by serving one tier table for both performance classes unless your own capture says otherwise; omit any claim that webgpu-disabled records still carry limits (2103-record absent cohort overlaps but does not equal the 580 disabled cohort) and never "clean up" the trailing-space key when re-serializing. Caveat: db.xz not graph-tracked; census evidence is direct-stream only.
