<!-- capsule-v2 -->
# Top knob ladders — hardware_concurrency 34-value spectrum, spec-capped device_memory, zero-information hls

**Source:** itbrowser-net/undetectable-fingerprint-browser no-LICENSE `main@6df77401149f82fa089589946859a92a0d9f6bb7`; Codebase Memory `undetectable-fingerprint-browser`. **Question:** What values may the four top-level identity knobs take, and which of them must never be randomized?

## Path/Symbol
**Path/Symbol:** `fingerprints/fingerprints.db.xz` → top-level `hardware_concurrency`, `device_memory`, `do_not_track`, `hls_enabled` (all present ×10000). Graph caveat: `not_tracked` artifact; plane absent from node surface (Retrieve → total 0).

## Signature
**Signature:** `{hardware_concurrency:int, device_memory:number, do_not_track:bool, hls_enabled:bool}`.

## Data Shape
- **hardware_concurrency spans exactly 34 distinct values** `[1..24, 28, 32, 35, 36, 40, 44, 48, 49, 56, 64]` (pass-7 correction: an earlier record said "33"; the executed unique-list says 34). Head: `{12×2332, 4×2091, 8×1898, 16×1409, 6×388, 2×371, 20×358, 24×354, 32×304, 3×88, 36×71, 28×55, …}`.
- **device_memory is spec-capped at 8:** `{0.5×64, 1×81, 2×132, 4×634, 8×9089}` — the Device Memory API reports ≤8 GiB; emitting 16 breaks the spec contract.
- **do_not_track** `{false×8571, true×1429}`.
- **hls_enabled is CONSTANT false ×10000** — a zero-information knob; randomizing it only breaks pack coherence.
- **hc×dm coupling:** every large-hc cohort reports dm 8 (`[12,8]×2304`, `[8,8]×1825`, `[4,8]×1742`, `[16,8]×1406`, `[20,8]×357`, `[24,8]×354`, `[6,8]×352`); `[4,4]×305` is the notable low-end pair.

### Decisive source
```jsonc
// fresh pass-7 stream probes (verbatim)
knobs   : {"dm8":9089,"hlsT":0,"hc12":2332,"dntT":1429}
hc vals : [1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,
           28,32,35,36,40,44,48,49,56,64]        // 34 distinct
couple  : dm8 & hc12 -> 2304 ; record count 10000
```

**Flow:** read all four knobs from the chosen record as one unit → expose hardware_concurrency/device_memory/do_not_track through their APIs → keep hls_enabled false unless your host genuinely serves HLS.
**Invariant:** device_memory never exceeds 8 (spec cap); hls_enabled never varies; hardware_concurrency stays inside the 34-value recorded set and couples with device_memory as captured.

**Probe:** `xz -dc fingerprints/fingerprints.db.xz | jq -c '{"dm8":[.[]|select(.device_memory==8)]|length,"hlsT":[.[]|select(.hls_enabled==true)]|length,"hc12":[.[]|select(.hardware_concurrency==12)]|length,"dntT":[.[]|select(.do_not_track==true)]|length}'` → `{"dm8":9089,"hlsT":0,"hc12":2332,"dntT":1429}` (executed pass 7); distinct-list probe `[.[].hardware_concurrency] | unique` → the 34-element array above (executed pass 7).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "undetectable-fingerprint-browser",
  query: "how to spoof css media queries installed font list navigator hardware concurrency fingerprint profile" });
// executed pass 7 -> total: 1, sole hit structural noise (__branch__.main) — plane absent from node surface
```

## Verdict
Adopt the four ladders and the coupling table verbatim; adapt exposure mechanics per host API; omit randomizing hls_enabled or exceeding the device_memory spec cap. Caveat: direct-stream evidence only.
