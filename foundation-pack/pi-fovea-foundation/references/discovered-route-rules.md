<!-- capsule-v2 -->
# Statistical route discovery — how does a repo teach you its unknown route DSL without LLM calls?

**Source:** pi-fovea MIT `DETACHED@217a103`; Codebase Memory `pi-fovea`. **Question:** A repo writes routes in a shape your rule pack never declared — how do you promote that shape into a working extractor without hand-labeling, while corpus junk (`assertEquals(...)`) dwarfs every real shape?

## Jeffreys-smoothed per-argument posterior promotion
**Path/Symbol:** `src/core/discover.ts:harvestFile/aggregateFiles/posterior/synthesize/promote/isCovered` (:31-183).
**Signature:** `harvestFile(lang, text): FileSigs` (sigKey `"lang|shape|method|argIdx"` → `[sites, pathSites]`); `posterior(pathN, n) = (pathN+0.5)/(n+1)`; `promote(sigs, pack): SynthesizedRule[]`.
**Data Shape:** Promotion gates: `n ≥ 4 sites AND files ≥ 2 AND p̂ ≥ 0.55`. Corpus audit (8 repos, 183 sigs n≥4): junk band < p̂≈0.27, real shapes > p̂≈0.75 — the cutoff sits mid-cliff at any repo size. Harvest is LINE-regex over source text (no ast-grep pass), stored compactly per file in facts (`sigs`).

### Decisive source
```ts
// The promotion statistic is a per-argument conditional: given the string arg
// at position i of call-shape (lang·shape·callee), how often does it classify
// as a path? A Jeffreys-smoothed posterior decides — not raw frequency, under
// which chaff like assertEquals(...) dwarfs every real shape.
const key = `${lang}|${shape}|${method}|${idxNow}`;
rec[0]++; if (classifyLiteral(lit) === "path") rec[1]++;
...
// Pattern synthesis: dummy metavars for non-path slots, $P at the proven
// position; TWO variants (exact arity + trailing $$$H absorb) because some
// dialects only match with explicit tail holes (Python `$X, $P, $$$H`).
case "recv": variants = [`$R.$M(${inner})`, `$R.$M(${inner}, $$$H)`]; break;
id: `implicit:${lang.toLowerCase()}:${shape}:${callee}:${argIdx}`, implicit: true,
// A discovery is only NEW when no existing rule already binds the callee
// with a compatible shape in that language (java:dec:GetMapping promotes nothing):
const isCovered = (sig, pack) => pack.some(r => r.langs.includes(sig.lang)
  && compileMethods(r.methods).test(sig.callee)
  && pats.some(p => shapeCompatPatterns[sig.shape].test(p)));
```
Callee denylist even at ~100% precision: fs/path/string-predicate names (`join, resolve, readFile, startsWith, includes, useParams…`) — membership tests hit the path column at high rate but never declare routes; dynamic `import()/require()` are covered by the import edge already.

**Flow:** harvest per-file histograms during fact passes → aggregate REPO-WIDE (a dependency update or style drift flips a marginal signature only when repo-wide evidence moves) → gate on n/files/posterior → skip shapes already covered by the pack → synthesize implicit rules → appended to the base pack with HALF hub conductance and a △ sigil → once a known rule matches any site of that hub it upgrades to first-class instantly (build.ts :1032-1035: hub is implicit only when EVERY site came from a discovered rule). Turn-sync reports discovered-hub churn but NEVER lets it escalate red alone.
**Invariant:** Discovery is statistics-gated autonomy: an unconfirmed hypothesis gets half weight and no verdict power; promotions aggregate over all files so evidence must move repo-wide; synthesized patterns always ship both exact-arity and `$$$H` tail variants.
**Probe:** `tests/discover.test.ts` — "junk with great frequency is rejected by precision" (assertEquals 120/30 sites rejected; wire 9/10 promoted); "tools with fewer than 4 sites or 2 files stay un-promoted"; "puts $P at the proven arg position and offers an arity tail variant"; integration "promotes the unknown jobm DSL surfaces as implicit half-weight hubs" on tests/fixtures/mini.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pi-fovea", query: "harvestFile promote posterior synthesize", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the per-argument conditional posterior, cliff-calibrated threshold (0.55 between measured bands), dual-variant synthesis, coverage dedup against the static pack, half-gravity probation with instant upgrade on corroboration. Adapt the denylist and shape taxonomy to your languages. Omit nothing — the calibration notes are the transferable part.
