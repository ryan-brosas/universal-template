<!-- capsule-v2 -->
# GREASE brand list — how do you fabricate Sec-CH-UA brand lists that survive UA-CH checks?

**Source:** itbrowser-net/undetectable-fingerprint-browser no-LICENSE `main@6df77401149f82fa089589946859a92a0d9f6bb7`; Codebase Memory `undetectable-fingerprint-browser`. **Question:** What exact shape must brands / full_version_list / Sec-CH-UA headers take so UA-CH-aware detectors accept them?

## Three entries, per-client GREASE permutation, version tiers aligned
**Path/Symbol:** `fingerprints/fingerprints.db.xz` stream field paths `.navigator.brands[]`, `.navigator.full_version_list[]`, `.navigator.full_version`. Graph coverage caveat: binary artifact — direct-stream evidence only.
**Signature:** `brands: {brand: string, version: string}[]` (major-only); `full_version_list: {brand: string, version: string}[]` (full semver); both length 3.
**Data Shape:** two observed records: [Chrome 115 | Not/A)Brand v99 at position 0] and [Chrome 117 | Not;A=Brand v8 at position 1]. Full-stream census of GREASE entries finds exactly the six canonical UA-CH permutations: Not)A;Brand v24 x1895, Not.A/Brand v8 x1867, Not?A_Brand v24 x1498, Not/A)Brand v99 x1439, Not;A=Brand v8 x1352, Not=A?Brand v99 x1300.

### Decisive source
```jsonc
// record A (Chrome 115): GREASE first
"brands":[{"brand":"Not/A)Brand","version":"99"},{"brand":"Google Chrome","version":"115"},{"brand":"Chromium","version":"115"}]
"full_version_list":[{"brand":"Not/A)Brand","version":"99.0.0.0"},{"brand":"Google Chrome","version":"115.0.5790.110"},{"brand":"Chromium","version":"115.0.5790.110"}]
// record B (Chrome 117): GREASE middle
"brands":[{"brand":"Google Chrome","version":"117"},{"brand":"Not;A=Brand","version":"8"},{"brand":"Chromium","version":"117"}]
"full_version_list":[{"brand":"Google Chrome","version":"117.0.5938.150"},{"brand":"Not;A=Brand","version":"8.0.0.0"},{"brand":"Chromium","version":"117.0.5938.150"}]
```

**Flow:** pick UA major N → pick ONE of the six canonical GREASE permutations and its position → build brands [real/N, GREASE/spec-version, Chromium/N] in that order → expand the same order into full_version_list with real full versions → emit matching Sec-CH-UA / Sec-CH-UA-Full-Version-List headers.
**Invariant:** WITHIN one client: brands[i].brand == full_version_list[i].brand for all i (same permutation, same position); every major equals the UA-string Chrome major; GREASE version is one of the canonical pairs (v8, v24, v99) — never invented. ACROSS clients: permutation and position vary freely (that variation is itself the realistic signal).
**Probe:** `xz -dc fingerprints/fingerprints.db.xz | strings -n 8 | grep -o '"brand":"Not[^"]*","version":"[0-9]*"' | sort | uniq -c | sort -rn | head -6` → emits exactly the six-permutation census above (executed pass 1). No test runner exists at pin; deterministic probe stands in.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "undetectable-fingerprint-browser", query: "brands full_version_list navigator", limit: 5 });
```

## Verdict
Adopt the triple shape, the six-canonical-GREASE vocabulary, intra-record permutation consistency, and cross-field major alignment; adapt brand names/version sources per target engine (Chromium here); omit hand-rolled two-entry lists, invented GREASE spellings, or a globally fixed GREASE position (disproved by records A/B).
