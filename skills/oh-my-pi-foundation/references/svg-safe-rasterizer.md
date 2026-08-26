<!-- capsule-v2 -->
# svg-safe-rasterizer — how do you rasterize untrusted SVG for a terminal image preview without file-backed resource loads?

**Source:** oh-my-pi MIT `main@2b66ee69f2`; Codebase Memory `oh-my-pi`. **Question:** What makes SVG preview safe (no local file/image loads, bounded canvas) and where does rendering run?

## rasterizeSvg
**Path/Symbol:** `crates/pi-natives/src/svg.rs` (`rasterize_svg`); consumed in `packages/coding-agent/src/cli/git-tui/state.ts`.
**Signature:** `rasterizeSvg(input: Uint8Array, max_width_px: u32, max_height_px: u32) -> Promise<Uint8Array>` (PNG).
**Data Shape:** In: raw SVG/SVGZ bytes + pixel bounds; out: PNG bytes via promise from the blocking pool. Caller passes `SVG_PREVIEW_MAX_PX = 2048` for both bounds.

### Decisive source
```rust
const MAX_RENDER_PIXELS: u64 = 16 * 1024 * 1024;
...
if u64::from(max_width_px) * u64::from(max_height_px) > MAX_RENDER_PIXELS {
	... "SVG render limits exceed the {MAX_RENDER_PIXELS}-pixel safety cap"
```
with parsing via `usvg` on a static `FONT_DB` built once (`database.load_system_fonts()`), no file-backed image resource resolution.

**Flow:** JS detects an SVG side during the sniff gate (`looksLikeSvg`) → reads bytes (≤ MAX_FILE_BYTES) → `rasterizeSvg(bytes, 2048, 2048)` → PNG handed to the terminal graphics protocol; parse+render execute on `task::blocking("svg.rasterize", ...)` so the JS event loop never stalls.
**Invariant:** The usvg tree is built WITHOUT resolving `<image href="file:...">`-style references (SVGs cannot trigger local file reads), and any requested canvas exceeding 16 M pixels is rejected up front — a malicious or accidental huge canvas fails closed.
**Probe:** `grep -nF 'MAX_RENDER_PIXELS' crates/pi-natives/src/svg.rs` → line `14` and `grep -nF 'load_system_fonts' crates/pi-natives/src/svg.rs` → line `18`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", query: "rasterizeSvg usvg resvg PNG terminal preview", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the fail-closed pixel cap + no-file-resolution rule and off-thread execution; adapt the image-protocol handoff; omit fontdb if you render text-free diagrams only. Coverage caveat: native crate tests cover the sync core; the JS glue is integration-tested.
