<!-- capsule-v2 -->
# Screen geometry cohorts — 664 real clusters, float32 dpr noise, and the outer_height asymmetry

**Source:** itbrowser-net/undetectable-fingerprint-browser no-LICENSE `main@6df77401149f82fa089589946859a92a0d9f6bb7`; Codebase Memory `undetectable-fingerprint-browser`. **Question:** Which `(width, height, dpr)` triples and screen-edge values may a profile emit without leaving the pack of REAL captured Windows displays?

## Path/Symbol
**Path/Symbol:** `fingerprints/fingerprints.db.xz` → `.screen` (11 keys, uniform ×10000: avail_left, avail_top, avail_width, avail_height, width, height, outer_width, outer_height, color_depth, pixel_depth, device_pixel_ratio). Graph caveat: `not_tracked` artifact; plane absent from node surface (Retrieve → total 0).

## Signature
**Signature:** `.screen` = `{avail_left:int, avail_top:int, avail_width:int, avail_height:int, width:int, height:int, outer_width:int, outer_height:null, color_depth:int, pixel_depth:int, device_pixel_ratio:float32}`.

## Data Shape
- **664 distinct `(width,height,dpr)` clusters**; head of the distribution is real-world Windows geometry: `1920×1080@1 ×4368`, `1536×864@1.25 ×1268` (125% scaling), `2560×1440@1 ×597`, `1366×768@1 ×550`.
- `device_pixel_ratio` takes **96 distinct float values** with visible float32 serialization noise (`0.800000011920929`, `1.1696667671203613`, `2.3980002403259277`) — scaled/zoomed real displays, not clean steps.
- `color_depth == pixel_depth` ALWAYS (`[24,24]×9906, [30,30]×93, [4,4]×1`; mixed count = 0).
- `avail_top` is 0 on 9257 records but carries NEGATIVE values to **−1440** (multi-monitor above primary) and small positives (taskbar heights); `avail_left` 0 on 8806 with ±1920/−2560/−3840 monitor offsets.
- **ASYMMETRY TRAP:** `outer_width` is populated on ALL records (`== width` on 9810, differs on 190) while `outer_height` is NULL on all 10000. A porter who "completes" `outer_height=height` leaves every real record in the pack behind.

### Decisive source
```jsonc
// fresh pass-7 stream probes (verbatim)
clusters : 664
top      : [{"g":{"w":1920,"h":1080,"d":1},"n":4368},{"g":{"w":1536,"h":864,"d":1.25},"n":1268},
            {"g":{"w":2560,"h":1440,"d":1},"n":597},{"g":{"w":1366,"h":768,"d":1},"n":550}]
asym     : {"oh_null":10000,"ow_null":0,"ow_eq_w":9810}
depth    : mixed = 0 ; avail_top min = -1440 ; dpr distinct = 96
```

**Flow:** select the whole screen object from the chosen record → inject verbatim → keep window/viewport code paths tolerant of `outer_height === null` and of viewport>screen pairs recorded in user-agents.json (452/10000 there).
**Invariant:** screens come in captured clusters, not a generator's imagination — sample the cluster, then derive avail_* only from the same record. Float32 dpr noise and negative avail offsets are authenticity signals, not bugs to round away.

**Probe:** `xz -dc fingerprints/fingerprints.db.xz | jq -c '[.[] | [.screen.width,.screen.height,.screen.device_pixel_ratio]] | unique | length'` → `664` (executed pass 7); and `xz -dc fingerprints/fingerprints.db.xz | jq -c '{"oh_null":[.[]|select(.screen.outer_height==null)]|length,"ow_null":[.[]|select(.screen.outer_width==null)]|length,"ow_eq_w":[.[]|select(.screen.outer_width==.screen.width)]|length}'` → `{"oh_null":10000,"ow_null":0,"ow_eq_w":9810}` (executed pass 7).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "undetectable-fingerprint-browser",
  query: "screen devicePixelRatio avail_left multi-monitor outer_height geometry cluster" });
// executed pass 7 -> total: 0 (plane absent from node surface; this capsule is the only path)
```

## Verdict
Adopt cluster-sampling with verbatim dpr floats and the null-outer_height contract; adapt coordinate systems per host OS; omit synthesizing plausible-but-unrecorded geometries or rounding dpr noise. Caveat: single-monitor bias of the pack itself is inherent to the source corpus.
