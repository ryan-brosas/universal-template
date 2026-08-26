<!-- capsule-v2 -->
# SVG rasterization guard — how do you render untrusted SVG into terminal-safe PNG previews without file-system or pixel-bomb exposure?

**Source:** oh-my-pi (see pack SKILL.md Provenance) MIT `main@2b66ee69f2`; Codebase Memory `oh-my-pi`. **Question:** What are the exact safety gates (resource resolution, canvas cap, off-thread execution) around `rasterizeSvg`?

## Bounded, file-blind rasterization
**Path/Symbol:** `crates/pi-natives/src/svg.rs:` `MAX_RENDER_PIXELS = 16 * 1024 * 1024` (:18), `rasterize_svg` napi wrapper (:31–40), `rasterize_svg_sync` (:42–70); TS binding `packages/natives/native/index.d.ts:1917`; consumer `decodeReviewImage` `packages/coding-agent/src/cli/git-tui/state.ts:229–246` with `SVG_PREVIEW_MAX_PX = 2048` (:28).
**Signature:** `rasterizeSvg(input: Uint8Array, maxWidthPx: number, maxHeightPx: number): Promise<Uint8Array>` (PNG out).
**Data Shape:** In: SVG/SVGZ bytes + per-axis max px; out: PNG scaled to fit (`scale = min(maxW/w, maxH/h, 1.0)`, ceil, ≥1px).

### Decisive source
```rust
if u64::from(max_width_px) * u64::from(max_height_px) > MAX_RENDER_PIXELS {
	return Err(... format!("SVG render limits exceed the {MAX_RENDER_PIXELS}-pixel safety cap"));
}
let mut options = usvg::Options { fontdb: Arc::clone(&FONT_DB), ..usvg::Options::default() };
// Repository-controlled SVGs must not read arbitrary host files through an
// <image href="…"> reference. Embedded data URLs retain the default resolver.
options.image_href_resolver.resolve_string = Box::new(|_, _| None);
```

**Flow:** napi entry copies the bytes and hops to the blocking pool (`task::blocking("svg.rasterize")`) so parsing/rendering never stalls the JS event loop → validate limits (zero rejected; w×h product capped at 16M pixels BEFORE any parse work) → parse with file-href resolution disabled (data URLs still allowed) → scale-to-fit never upscales beyond intrinsic size → tiny_skia pixmap render → PNG encode. Consumer arm: git-TUI's image classifier routes SVG-looking blobs here and wraps the result as a base64 PNG ReviewImage (`sourceMimeType:"image/svg+xml"`).
**Invariant:** The href kill-switch is the security boundary — without it a repo-controlled `.svg` diff preview becomes arbitrary-file read via `<image href="/etc/passwd">`. Errors are typed strings for invalid SVG / zero-or-oversized limits / allocation / encode failure; callers treat failure as "no preview", never as pane failure. Rust unit tests pin BOTH the happy path (12×7 intrinsic stays 12×7) and the cap rejection (`assert!(error.reason.contains("safety cap"))` at :88).
**Probe:** No JS-side test drives rasterize directly (addon-dependent suite skipped honestly); Rust tests `crates/pi-natives/src/svg.rs:76-89` pin behavior — verified byte-exact by read at pin. Deterministic greps: `resolve_string = Box::new(|_, _| None)` @svg.rs:55, `16 * 1024 * 1024` @:18.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", query: "rasterize_svg svg png render limits", limit: 10, fields: ["signature", "name", "file"] });
```
Live-resolved @2b66ee69: `rasterize_svg svg.rs:31-40`, `rasterize_svg_sync :42-70`.

## Verdict
Adopt all four gates (pixel pre-cap, zero-limit rejection, href blindness, off-thread) for ANY untrusted-vector rendering; adapt resvg to your stack but keep resolve_string neutered unless you can prove input provenance. Omit the terminal-image wrapping if you display differently.
