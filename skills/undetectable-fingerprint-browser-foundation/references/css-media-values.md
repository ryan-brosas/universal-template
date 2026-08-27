<!-- capsule-v2 -->
# CSS media values — presence-gated keyset as Chromium-generation proxy plus exact derived ratios

**Source:** itbrowser-net/undetectable-fingerprint-browser no-LICENSE `main@6df77401149f82fa089589946859a92a0d9f6bb7`; Codebase Memory `undetectable-fingerprint-browser`. **Question:** Which media-query answers must a profile emit so feature-detection probes place it in a coherent Chromium generation — and which values are pure derivations?

## Path/Symbol
**Path/Symbol:** `fingerprints/fingerprints.db.xz` → `.css{}` (media-feature map; keyset is PRESENCE-GATED per record). Graph caveat: `not_tracked` artifact; plane absent from node surface (Retrieve → total 0).

## Signature
**Signature:** `.css = Record<MediaFeatureName, string | number | [number,number]>`; 24-key corpus union, but NO record carries all 24.

## Data Shape
- Presence: 20 keys ×10000; `update` + `overflow-block` ×9432; `prefers-reduced-transparency` ×2824; `prefers-contrast` ×9998 (missing on exactly 2); `inverted-colors` ×5 (all `"none"`, majors 117–119).
- **Version-proxy law (executed cross-tab):** no-`update` ⇒ old-era captures (majors mass 102–117); `update`-only ⇒ majors 107–119; both-present ⇒ majors 110–121 (118×1300 · 119×1496 · 120×12 · 121×3). Monotone WITH an anomaly tail — feature presence tracks shipping cohorts, not a hard function of major.
- **DERIVED ratios hold exactly on ALL records:** `aspect-ratio ≡ width·10⁴/height` and `device-aspect-ratio ≡ device-width·10⁴/device-height` (violation counts 0 at ±1 tolerance); `resolution` mirrors `dpr·96`: `{96×6994, 120×1709, 144×482, …}`.
- Small vocab ladders: pointer `{fine×9966, coarse×19, none×15}`; any-pointer `{fine×9631, coarse×354, none×15}`; color-gamut `{srgb×9598, p3×401, rec2020×1}`; hover==any-hover `{hover×9964, none×36}`; orientation `{landscape×9909, portrait×91}`; prefers-color-scheme `{light×6842, dark×3158}`; prefers-reduced-motion `{no-preference×8572, reduce×1428}`; prefers-reduced-transparency `{no-preference×2519, reduce×305}` when present. CONSTANTS: color-index 0, grid 0, monochrome 0, overflow-block scroll, update fast. Highest-cardinality keys are viewport/screen echoes: aspect-ratio 1921 distinct forms.

### Decisive source
```jsonc
// fresh pass-7 stream probes (verbatim)
gates : {"upd":9432,"rt":2824,"pc_missing":2,"ic":5}
ar_bad: 0        // |aspect-ratio - width*10000/height| > 1 count
res   : [{"v":96,"n":6994},{"v":120,"n":1709},{"v":144,"n":482},{"v":105,"n":104},
          {"v":192,"n":96}, {"v":86,"n":69}, ...70 forms total]
```
(This capsule REPLACES the pass-2 claim of a "uniform 24-key union" — refuted by execution in pass 4 and re-executed pass 7.)

**Flow:** pick record → read its css KEYSET as the generation fingerprint → emit matchMedia answers only for keys present in the record → compute aspect-ratio/resolution from the same record's dims/dpr, never independently.
**Invariant:** the keyset itself is signal — emitting `update`/`prefers-reduced-transparency` on an old-generation identity is a cross-field tell; derived ratios must be recomputed from the SAME record's dimensions or omitted, never randomized.

**Probe:** `xz -dc fingerprints/fingerprints.db.xz | jq -c '{"upd":[.[]|select(.css|has("update"))]|length,"rt":[.[]|select(.css|has("prefers-reduced-transparency"))]|length,"pc_missing":[.[]|select((.css|has("prefers-contrast"))|not)]|length,"ic":[.[]|select(.css|has("inverted-colors"))]|length}'` → `{"upd":9432,"rt":2824,"pc_missing":2,"ic":5}` (executed pass 7); derivation check `[.[] | select((((.css["aspect-ratio"] // -1) - ((.css.width // 0) * 10000 / (.css.height // 1))) | fabs) > 1)] | length` → `0` (executed pass 7).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "undetectable-fingerprint-browser",
  query: "how to spoof css media queries installed font list navigator hardware concurrency fingerprint profile" });
// executed pass 7 -> total: 1, sole hit is structural noise (__branch__.main Branch node)
```

## Verdict
Adopt presence-gated keysets with the generation-proxy cross-tab and the two exact derivations; adapt value serialization to your matcher; omit uniform full-key emission. Caveat: db-plane evidence is direct-stream only.
