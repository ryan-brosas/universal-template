<!-- capsule-v2 -->
# GP qualifier with BALD acquisition — why GPR instead of a classifier, and how do anchors enter the fit?

**Source:** OpenOutreach GPL-3.0 `main@c3ac1434118ac5301b193506d1d01e6e313bc622`; Codebase Memory `openoutreach`. **Question:** How do you build an uncertainty-aware binary ranker on small, imbalanced, incrementally-arriving label data — and where exactly do synthetic positives sit in the training arrays?

## Connected graph-selected seam
**Path/Symbol:** `openoutreach/core/ml/qualifier.py:BayesianQualifier._fit_if_needed` (:312-362), `_training_arrays` (:297-301), `compute_bald` (:429-455), `predict_probs` (:461-469), `_balance` (:364-392).
**Signature:** `update(embedding, label)`; `set_anchors(embeddings)`; `predict(embedding) -> (p, entropy, std) | None`; `compute_bald(X: (N, dim)) -> np.ndarray | None`.
**Data Shape:** Pipeline(StandardScaler → GaussianProcessRegressor(ConstantKernel(1.0)·RBF(length_scale=√384), n_restarts_optimizer=3, alpha=0.1)); labels 0/1; `_fitted` dirty flag ⇒ lazy refit over ALL accumulated data.

### Decisive source
```python
def _training_arrays(self):
    X = self._X + self._anchor_X
    y = self._y + [1] * len(self._anchor_X)      # anchors = permanent label-1 rows,
    return np.array(X), np.array(y)              # never trimmed, never displaced

X_fit, y_fit = (X_arr, y_arr) if self.is_cold else self._balance(X_arr, y_arr)
# balancing SKIPPED while cold: subsampling would discard real rejections to match a
# positive class still mostly invented (_MAX_IMBALANCE_RATIO = 2 afterwards)

def compute_bald(self, embeddings):
    f_mean, f_std = _gpr_predict(self._pipeline, embeddings)
    f_samples = f_mean + f_std * self._rng.randn(self._n_mc_samples, len(f_mean))
    p_samples = norm.cdf(f_samples - 0.5)        # probit link per MC sample
    return _binary_entropy(p_samples.mean(0)) - _binary_entropy(p_samples).mean(0)
```

**Flow:** every `update`/`set_anchors` sets `_fitted=False` → next prediction refits the whole pipeline → probabilities are P(f>0.5)=norm.sf from the GP posterior (naturally in [0,1], no clipping) → BALD = H(E[p]) − E[H(p)] via 100 MC samples for candidate selection.
**Invariant:** GPR not GPC deliberately: exact closed-form posterior avoids the degenerate-0.5 problem GPC has on weakly separable embedding data. The fit is O(n³) and announced BEFORE it runs ("17s at 1,220 labels") because the longest stall in the loop must explain itself. Anchors keep the positive class alive permanently so the model is never single-class; class_counts count them as positives forever, but the cold-phase *clock* (`is_cold`) is independent: `n_real_positives < ANCHOR_COUNT`.
**Probe:** `tests/ml/test_qualifier.py::TestBayesianQualifierUpdate` (:26-58), `TestBaldScores` (:88-116), `TestAnchors` (:211-327).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openoutreach", query: "compute_bald", limit: 5 });
```

## Verdict
Adopt: GPR+probit as the uncertainty-aware binary scorer; lazy full-refit behind a dirty flag when datasets are small; anchors concatenated into training arrays as permanent positives; imbalance cap skipped during cold phase; MC-probit BALD for informativeness. Adapt kernel length scale to your embedding dim/geometry; omit joblib persistence details unless you also persist pipelines to DB blobs.
