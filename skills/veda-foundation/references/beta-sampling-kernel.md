<!-- capsule-v2 -->
# Beta sampling kernel — how do you sample Thompson-Sampling posteriors without a seeded RNG and still bound early exploitation?

**Source:** Veda (`veda-ts`, MIT, `master@c3c69f2c340ec81ada8ea974076ce5bbaf5ccbc6`); Codebase Memory `veda`. **Question:** The module-selection ladder samples Beta(wins+1, losses+1) posteriors. How are Beta variates produced from Math.random alone, and what keeps a lucky 1/1 module from being treated as proven?

## Gamma-ratio Beta + Wilson lower bound
**Path/Symbol:** `src/stats/sampling.ts` (whole, 86L): `sampleBeta` (:14-18), `gammaVariate` (:23-49, private), `normalVariate` (:54-59, private), `wilsonLower` (:73-86); co-located test `src/stats/sampling.test.ts`.
**Signature:** `sampleBeta(alpha: number, beta: number) → number`; `wilsonLower(wins: number, n: number, z = 1.96) → number`.
**Data Shape:** `sampleBeta` returns [0,1]; `wilsonLower` returns the 95% lower bound of the true win rate (0 for n=0).

### Decisive source
```ts
export function sampleBeta(alpha: number, beta: number): number {
  const a = gammaVariate(alpha);
  const b = gammaVariate(beta);
  return a / (a + b);
}

// shape < 1: Ahrens-Dieter — Gamma(shape) = Gamma(shape+1) * U^(1/shape)
// shape >= 1: Marsaglia-Tsang squeeze
const d = shape - 1 / 3;
const c = 1 / Math.sqrt(9 * d);
// ... do { x = normalVariate(); v = 1 + c * x; } while (v <= 0);
// v = v*v*v; quick accept: u < 1 - 0.0331 * x^4; slow accept: log(u) < 0.5*x*x + d*(1 - v + log(v))

export function wilsonLower(wins: number, n: number, z = 1.96): number {
  if (n === 0) return 0;
  const p = wins / n;
  const zsq = z * z;
  const denom = 1 + zsq / n;
  const center = p + zsq / (2 * n);
  const spread = z * Math.sqrt((p * (1 - p) + zsq / (4 * n)) / n);
  return Math.max(0, (center - spread) / denom);
}
```
**Flow:** each selection draws `sampleBeta(wins+1, losses+1)` per module and the argmax wins (see module-selection-ladder capsule) → the Beta posterior's variance IS the exploration pressure: an untried module Beta(1,1) is uniform, so it sometimes beats a proven winner; no seeded RNG is needed because determinism lives in the pairwise judge seeds, not in module selection → `wilsonLower` is the display/ranking-side bound that keeps small-sample win rates honest (1/1 → ≥21%, 10/10 → ≥72%, 0/5 → ≥0%).
**Invariant:** the sampler is stateless (every call independent, `Math.random` only) — safe to call from any concurrency context without locks; fractional shapes (alpha or beta < 1) route through the Ahrens-Dieter branch, so posteriors from 0-win/1-win modules are valid.
**Probe:** `src/stats/sampling.test.ts` (executed live at pin: 14 pass / 0 fail, 482 expect) pins the [0,1] range, Beta(1,1)≈uniform mean, Beta(10,1)/Beta(1,10) concentration, the shape<1 branch, and the Wilson bound table (1/1→~0.21 etc.).
**Coverage caveat:** statistical tests are distributional (1000-sample means), not exact-value pins; a port should keep the tolerance-style assertions rather than exact values.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "veda", query: "sampleBeta gammaVariate wilsonLower Thompson sampling Beta posterior", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the gamma-ratio Beta sampler (Marsaglia-Tsang + Ahrens-Dieter) and the Wilson lower bound for small-sample honesty. Adapt the z-score and the RNG source. Omit Wilson if your UI never displays win rates.
