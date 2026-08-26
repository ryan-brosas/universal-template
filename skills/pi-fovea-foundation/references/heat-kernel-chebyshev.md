<!-- capsule-v2 -->
# Chebyshev heat kernel — how do you evaluate e^{-tL} over a code graph cheaply at many timescales?

**Source:** pi-fovea MIT `DETACHED@217a1034386d5d8a6a7d6a75a6e1903109398630`; Codebase Memory `pi-fovea`. **Question:** A porter wants repo-map relevance as graph diffusion but must not re-run an O(K·nnz) matrix exponential per query/timescale — what does pi-fovea cache, and why is there NO Jackson window?

## Chebyshev heat kernel with shared recurrence vectors
**Path/Symbol:** `src/core/heat.ts:besselI/heatCoeff/chebyshevVectors/heatField/chooseOrder/taylorReference` (:83-194).
**Signature:** `chebyshevVectors(csr: Csr, s: Float64Array, K: number): Float64Array[]`; `heatField(tk: Float64Array[], t: number, n: number): Float64Array`; `chooseOrder(t): number = min(90, ceil(2.2*t)+16)`; `heatAt(csr, s, t)` one-shot.
**Data Shape:** `tk[k] = T_k(M)s` with `M = L − I` (spectrum [−1,1]); coefficients `c_k(t) = e^{-t}·I_k(t)` for k=0, else `2·(−1)^k·e^{-t}·I_k(t)` where I_k is the modified Bessel function computed via log-space series (`logAddExp` + Lanczos-free Stirling `gammaLn`). The four ops share ONE walk: sketch t=16, focus t=2, dwell t×factor ≤ 64, impact t=4.

### Decisive source
```ts
// tk vectors are cached in the session and every later dwell-for-a-new-t
// costs O(K*n), not O(K*nnz). The operator is the index.
export const chebyshevVectors = (csr: Csr, s: Float64Array, K: number): Float64Array[] => {
  const tk: Float64Array[] = new Array(K + 1);
  tk[0] = Float64Array.from(s);
  if (K >= 1) tk[1] = applyNegP(csr, tk[0]!);
  for (let k = 2; k <= K; k++) {
    const prev = tk[k - 1]!;
    const mv = applyNegP(csr, prev);
    const out = new Float64Array(csr.n);
    const p2 = tk[k - 2]!;
    for (let i = 0; i < csr.n; i++) out[i] = 2 * mv[i]! - p2[i]!;
    tk[k] = out;
  }
  return tk;
};
export const heatField = (tk: Float64Array[], t: number, n: number): Float64Array => {
  // v += c_k · tk[k], skipping |c|<1e-16 — recombination only.
};
```
```ts
// heat.ts header comment — the no-window decision:
// No Jackson damping window on the coefficients, deliberately: SGWT applies
// windowing because its wavelet-frame kernels are compactly-supported bumps
// (Gibbs ringing at the support edge). The heat kernel e^{-t(1+mu)} is smooth
// on [-1,1], so plain truncation error decays superalgebraically (measured
// ~6e-9 ...); a Jackson window would *reduce* pointwise accuracy.
```

**Flow:** seed vector → one chebyshev pass builds tk[0..K] → any timescale recombines cached vectors with Bessel coefficients → dwell extends the recurrence ONLY when `chooseOrder(to) > tk.length−1` (ops.ts :869-874, `tkKey += "+ext"`), never silently degrading accuracy.
**Invariant:** The T_k(M)s vectors depend on the SEEDS, not on t — cache them per focus key (`session.tkKey`) and reuse across all t; a new t must never trigger a new graph walk. Session stores TK_ORDER=80 vectors covering dwell up to t≈33 "with full accuracy" (session.ts :28); beyond that extend, don't degrade.
**Probe:** `tests/heat.test.ts` — "Chebyshev heat matches the Taylor reference at several times" (maxDiff < 1e-8 vs scaling-and-squaring `taylorReference`, independent in structure AND coefficients); "dwell monotonicity: increasing t strictly widens the lit set"; "besselI matches known values" (I_0(3)=4.880792585865…).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pi-fovea", query: "heatField chebyshev", limit: 10, fields: ["signature", "name", "file"] });
// → pi-fovea.src.core.heat.heatFunction src/core/heat.ts 145-155
```

## Verdict
Adopt the shared-Chebyshev-recurrence design (walk once, recombine per timescale), the no-Jackson-window decision for smooth heat kernels, and the order formula `min(90, ⌈2.2t⌉+16)` with explicit extension past the cached order. Adapt `chooseOrder` caps to your graph size and t range. Omit the Taylor reference implementation (test-only). Caveat: none — dual-implementation numeric test is the probe.
