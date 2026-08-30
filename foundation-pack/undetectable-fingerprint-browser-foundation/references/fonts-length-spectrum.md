<!-- capsule-v2 -->
# Fonts length spectrum — a real installed-font-count distribution, not a band

**Source:** itbrowser-net/undetectable-fingerprint-browser no-LICENSE `main@6df77401149f82fa089589946859a92a0d9f6bb7`; Codebase Memory `undetectable-fingerprint-browser`. **Question:** How many fonts may a profile claim so font-probing detectors (measure text width across a candidate list) see a plausible Windows install?

## Path/Symbol
**Path/Symbol:** `fingerprints/fingerprints.db.xz` → `.fonts[]` — integer index array into a product-private font-name table (resolver not in this repo; index-indirection caveat). Graph caveat: `not_tracked` artifact; plane absent from node surface (Retrieve → total 0).

## Signature
**Signature:** `.fonts = int[10..1518]` with **495 distinct lengths** across the corpus.

## Data Shape
- Range **10..1518**; modes `201 ×1186` and `381 ×624`; secondary mass 230–232 ({135,290,200}), a 199–204 cluster, a 377–396 band peaking at 381, and long tails >1000 (`1335×9, 1512×2, 1513×11, 1212×1 …`); singleton extremes 10 and 72.
- This is a real installed-font-count spectrum — NOT the tight 31..37 band headers show (vocab-order-planes). Length correlates loosely with capture era and machine role; no deterministic function to hardware_concurrency was established (standing on-demand drill).
- Per-font-NAME membership is unresolvable in-repo: indexes point into the binary's vocabulary.

### Decisive source
```jsonc
// fresh pass-7 stream probe (verbatim)
{"min":10,"max":1518,"m201":1186,"m381":624,"forms":495}
```
(Probe-form erratum carried from pass 4: an early draft eyeballed "~380 distinct"; execution says 495.)

**Flow:** sample length from the recorded spectrum (mode-weighted) OR copy a record's array verbatim → resolve names only through your own installed-font table → keep the array length stable across all probes of the same identity.
**Invariant:** font COUNT is a cohort signal; jumping between mode values (201↔381) between sessions of one identity is as tell-tale as claiming an unrecorded extreme. Never emit a length outside 10..1518.

**Probe:** `xz -dc fingerprints/fingerprints.db.xz | jq -c '{"min":[.[]|.fonts|length]|min,"max":[.[]|.fonts|length]|max,"m201":[.[]|select((.fonts|length)==201)]|length,"m381":[.[]|select((.fonts|length)==381)]|length,"forms":[.[]|.fonts|length]|unique|length}'` → `{"min":10,"max":1518,"m201":1186,"m381":624,"forms":495}` (executed pass 7).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "undetectable-fingerprint-browser",
  query: "how to spoof css media queries installed font list navigator hardware concurrency fingerprint profile" });
// executed pass 7 -> total: 1, sole hit structural noise (__branch__.main) — plane absent from node surface
```

## Verdict
Adopt the spectrum bounds and mode-weighted sampling; adapt name resolution to your host's font inventory; omit uniform or rounded counts (500/1000 are not in the distribution's mass). Caveat: name-level tables live outside the repo.
