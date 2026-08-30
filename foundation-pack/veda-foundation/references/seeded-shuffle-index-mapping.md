<!-- capsule-v2 -->
# Seeded shuffle index mapping — deterministic candidate order with lossless position recovery

**Source:** Veda (`veda-ts`, MIT, `master@f050518c99fa54a5a0af4a04918aaf01d1ed94e1`); Codebase Memory `veda`. **Question:** How do I present shuffled candidates to an LLM judge yet map its chosen DISPLAY position back to the original candidate deterministically?

## splitmix-style seeded PRNG + Fisher-Yates over an index array
**Path/Symbol:** `src/core/judge-format.ts:shuffle` (:33–63) exposed as `shuffleCandidates` (:146–148); consumed by `XML_JUDGE_FORMAT.format/parse` (:65–144).
**Signature:** `function shuffle<T>(arr: T[], seed?: string): { shuffled: T[]; indexMapping: number[] }` — `indexMapping[displayIdx] = originalIdx`.
**Data Shape:** seed → 32-bit accumulator via `seedNum = (seedNum << 5) - seedNum + charCode |= 0`; each draw advances `seedNum += 0x9e3779b9 | 0` then two `Math.imul` mixes; unseeded calls fall back to `Math.random()` (non-reproducible by design).

### Decisive source
```ts
const random = () => {
  if (seed === undefined) return Math.random();
  seedNum = (seedNum + 0x9e3779b9) | 0;
  let t = Math.imul(seedNum ^ (seedNum >>> 16), 0x21f0aaad);
  t = Math.imul(t ^ (t >>> 15), 0x735a2d97);
  return ((t = t ^ (t >>> 15)) >>> 0) / 4294967296;
};
for (let i = copy.length - 1; i > 0; i--) {
  const j = Math.floor(random() * (i + 1));
  [copy[i], copy[j]] = [copy[j], copy[i]];
}
return { shuffled: copy.map(i => arr[i]), indexMapping: copy };
```

**Flow:** build identity index array → Fisher-Yates descending using seeded draws → `shuffled` is candidates reordered, `indexMapping` is the permutation itself. Prompt shows `Candidate ${displayIdx+1}` blocks; the judge's `<best>N</best>` answer is clamped into `[0, mapping.length-1]` then translated via `indexMapping[clamped]`.
**Invariant:** The mapping array is the single source of truth for de-shuffling; prompt construction and parsing MUST share one mapping instance. Same seed ⇒ same permutation ⇒ reproducible judge runs (the deep pipeline persists `judgeSeed` in checkpoints exactly for this).
**Probe:** `tests/core/judge-format.test.ts` — `respects shuffled order via index mapping` (:34), `maps display index back to original via mapping` (:80), `clamps out-of-bounds index` (:99).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pi-ecosystem-veda", query: "shuffleCandidates indexMapping seed", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the PRNG constants (golden-ratio increment + imul mix) and the index-mapping pattern — any LLM-judge panel needs position-debiasing with recovery. Adapt seed derivation if your host already has a hash primitive. Omit the XML prompt template itself (owned by judge capsules) but keep format+parse sharing ONE mapping.
