<!-- capsule-v2 -->
# DB WebGL interior — three properties-map shapes signal the capability tier, not renderer vintage

**Source:** itbrowser-net/undetectable-fingerprint-browser no-LICENSE `main@6df77401149f82fa089589946859a92a0d9f6bb7`; Codebase Memory `undetectable-fingerprint-browser`. **Question:** How does a db record encode WebGL1/WebGL2 capability tier internally, and which property values are ladders versus constants?

## Path/Symbol
**Path/Symbol:** `fingerprints/fingerprints.db.xz` → `.webgl{}` — 12 keys: the 8 `webgl.json` surfaces in snake_case PLUS `extensions[]`, `extensions2[]` (index arrays), `max_anisotropy`, `properties{}`. Graph caveat: `not_tracked` artifact; plane absent from node surface (Retrieve → total 0).

## Signature
**Signature:** `.webgl.properties = Record<GLParamName, string|[string,string]|number>` with WebGL2 twins stored as the same key suffixed `2`.

## Data Shape
- **THREE shapes, exactly:** `{157 keys, 92 "*2" twins} ×9749` (full WebGL2) vs `{63 keys} ×190` and `{65 keys} ×61` legacy cohorts (zero twins; `version2 == null`, `shading_language2 == null`, `extensions2 == [[43]] UNIQUE across all 251`).
- **Tier is signaled by KEYSET SHAPE, not renderer vintage** — the legacy cohort includes modern D3D11 vs_5_0 GPUs (e.g., Radeon RX 480) that merely lack WebGL2.
- `version2` on the full cohort is dominated by `"WebGL 2.0 (OpenGL ES 3.0 Chromium)"` but carries FOUR rare non-ES variants verbatim (`"WebGL 1.0"`, `"WebGL 1.0 (OpenGL Chromium)"`, `"WebGL 1.0 (OpenGL)"`); `shading_language2` includes the malformed truncated form `"WebGL GLSL ES (OpenGL Chromium"` kept as-is.
- Capability ladders INSIDE properties: `maxTextureSize {"16384"×8733, "8192"×1230, "32768"×20, "4096"×17}` (STRING-serialized); `max_anisotropy {16×9987, 4×7, 8×4, 2×2}`. Value-variance census: ~50 property keys corpus-constant, ~107 vary; most-varying is `aliasedPointSizeRange {["1","1024"]×8827, ["1","1023"]×954, ["1","256"]×162, ["1","8192"]×28, ["1","2047"]×7, ["1","1"]×6}`.
- Extension-array length ladders: e1 mode 29×9553 (spread 22..36), e2 mode 19×7145 (spread 16..24).

### Decisive source
```jsonc
// fresh pass-7 stream probes (verbatim)
cohorts : [{"g":{"plen":157,"twon":92},"n":9749},{"g":{"plen":63,"twon":0},"n":190},
           {"g":{"plen":65,"twon":0},"n":61}]
leg e2  : [[43]]                                  // unique legacy extensions2 value
mts     : [{"v":"16384","n":8733},{"v":"8192","n":1230},{"v":"32768","n":20},{"v":"4096","n":17}]
modes   : {"e1mode":{"v":29,"n":9553},"e2mode":{"v":19,"n":7145}}
```

**Flow:** classify record by `(properties|keys|length, twin count)` FIRST → if legacy, answer WebGL2 contexts as unavailable and return `[[43]]` for extensions2 → if full, serve the record's own ladders (maxTextureSize/anisotropy/point-size ranges) verbatim.
**Invariant:** never pair a legacy keyset with populated `*2` strings or vice versa; keep string serialization of numeric GL limits (`"16384"`) — real captures quote them.

**Probe:** `xz -dc fingerprints/fingerprints.db.xz | jq -c '[.[] | {plen:(.webgl.properties|keys|length), twon:[.webgl.properties|keys[]|select(test("2$"))]|length}] | group_by([.plen,.twon]|tostring) | map({g:(.[0]),n:length})'` → the three-cohort table above (executed pass 7); and `[.[] | select((.webgl.properties|keys|length)==63) | .webgl.extensions2] | unique` → `[[43]]` (executed pass 7).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "undetectable-fingerprint-browser",
  query: "maxTextureSize aliasedPointSizeRange extensions properties WebGL2 twin legacy cohort" });
// executed pass 7 -> total: 0 (plane absent from node surface; this capsule is the only path)
```

## Verdict
Adopt shape-first classification and the verbatim ladder tables; adapt naming to your GL surface map; omit inferring tier from renderer strings. Caveat: webgl.version2's four non-dominant variants ↔ backend linkage remains an ON-DEMAND drill (research.md §PASS-5 target #2).
