<!-- capsule-v2 -->
# aspect-aware-clamp-size — How do you fit an arbitrary capture size under a "max resolution" without distorting ultrawide/ultratall displays or producing odd dimensions?

**Source:** cap AGPL-3.0 `main@0ce9e67516b14449c4263c0b173c85c40f30421b`; Codebase Memory `ext-cap`. **Question:** What are the four aspect branches of the clamp, what does max_output_size mean on each axis, and why must every dimension be even?

## 16:9-ish → cap long edge; 9:16-ish → swap; ultrawide/ultratall → cap SHORT edge via max_short_edge = max×9/16; always even
**Path/Symbol:** `crates/recording/src/instant_recording.rs:736-776` (`clamp_size`), macOS-only constraint variant `:720-734` (`capture_size_constraint`), evenness helper `ensure_even`, application at `:319-334` (`create_pipeline`).
**Signature:** `fn clamp_size(input: (u32,u32), max: (u32,u32)) -> (u32,u32)` with `max.1 = (max.0 as f64 / 16.0 * 9.0) as u32` supplied by the caller.
**Data Shape:** Input raw capture pixels; `max_output_size` semantics = LONG-edge budget for near-16:9, but for ultrawide the height is capped at `max_output_size × 9/16` and width floats by ratio.

### Decisive source
```rust
// 16/9-ish
if input.0 >= input.1 && (input.0 as f64 / input.1 as f64) <= 16.0 / 9.0 {
    let width = ensure_even(max.0.min(input.0));
    let height_ratio = input.1 as f64 / input.0 as f64;
    let height = ensure_even((height_ratio * width as f64).round() as u32);
    (width, height)
}
// ultrawide (> 16:9): height = min(max_short_edge, input height), width follows ratio
```

**Flow:** Branch order matters: landscape-but-not-ultrawide first, portrait mirror second, then ultrawide, then ultratall (which SWAPS which component of `max` it reads — comment: "swapped since max_width/height assume horizontal"). Every produced dimension passes `ensure_even` after rounding — H264 chroma subsampling requires even dims.
**Invariant:** Ratio fidelity beats budget adherence: never crop, only scale; rounding happens AFTER scaling, and evenness is enforced per-dimension at the end (rounding to even can shift ±1px). The unreachable else is intentional — the four branches partition all positive inputs.
**Probe:** `crates/recording/src/instant_recording.rs:780-902` — tests `capture_size_constraint_preserves_instant_output_axis`, `test_clamp_size_16_9_ish_landscape`, `test_clamp_size_9_16_ish_portrait`, `test_clamp_size_ultrawide`, `test_clamp_size_ultratall`, `test_clamp_size_edge_cases`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-cap", query: "clamp_size capture_size_constraint instant", limit: 10 });
```

## Verdict
Adopt the four-branch clamp + even-dimension post-rounding. Adapt resolution tiers (FREE=1280, PRO=1920 from defaults.rs) to your product.
