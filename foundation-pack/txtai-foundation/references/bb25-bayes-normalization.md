<!-- capsule-v2 -->
# BB25 Bayesian normalization — sigmoid calibration that makes BM25 scores probability-like

**Source:** txtai Apache-2.0 `main@a10667a` (9.13.0); Codebase Memory `ext-txtai`. **Question:** How must raw keyword scores be calibrated into [0,1] probabilities so downstream fusion can treat them as log-odds inputs?

## Connected graph-selected seam
**Path/Symbol:** `src/python/txtai/scoring/normalize.py:Normalize.bayes` (:81-120), `.isbayes` (:39-47), `.default` (:63-79); aliases wired in `__init__` (:21-37).
**Signature:** `Normalize(config)` with method ∈ {bayes, bayesian, bayesian-bm25, bb25}; `__call__(scores, avgscore)` → normalized [(uid, score)].
**Data Shape:** input [(uid, raw_score)]; optional overrides alpha (default 1.0), beta (default None → dynamic median).

### Decisive source
```python
# Follow BB25 candidate-set behavior:
#   - estimate statistics on positive-score candidates only
#   - assign zero-score candidates a final score of 0.0
positive = values > 0.0
if not np.any(positive):
    return [(uid, 0.0) for uid, _ in scores]

candidates = values[positive]

# Dynamically derive beta using candidate score distribution, if not configured
beta = self.beta if self.beta is not None else float(np.median(candidates))

# Scale alpha by standard deviation for score-range invariance
std = float(np.std(candidates))
alpha = abs(self.alpha / std if std > 0 else self.alpha)

logits = np.clip(alpha * (candidates - beta), -500, 500)
probabilities[positive] = 1.0 / (1.0 + np.exp(-logits))
```

**Flow:** collect scores → zero-score docs STAY 0.0 → stats (median/std) from positive candidates only → logit = clip(α(score − median)) → sigmoid → [0,1] probabilities preserving rank order.

**Invariant:** Statistics are candidate-set-local (per query), NOT index-global — this is what makes the calibration score-range invariant and why the same doc can calibrate differently under different queries. Default normalization (`default()`) instead anchors on `avgscore` (`min(top+avg, 6*avg)` cap). The median-centering + 1/std scaling math is duplicated in LogOdds.calibrate (hybrid.py:177-200) — port both together or neither. Zero-stays-zero is asserted by test.

**Probe:** `test/python/testscoring/testkeyword.py:normalize` :391-398 — direct `Normalize("bb25")` call asserting zero stays 0.0 and monotonicity across positive scores; ranking-preservation asserts at :377-389.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-txtai", query: "Normalize bayes median alpha sigmoid bb25", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt positive-candidate-only statistics + dynamic beta/alpha + zero-preserving sigmoid; adapt alpha prior; omit if your fusion only consumes ranks (RRF path needs none of this).
