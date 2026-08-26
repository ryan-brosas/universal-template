<!-- capsule-v2 -->
# Negative signals audit — the penalty side: promotional density, thin content, stuffing, boilerplate, mixed signals

**Source:** GeoReady (Geo Optimizer) MIT `main@a7165be2`; Codebase Memory `ext-aeo-geo-optimizer-skill`. **Question:** Which page traits reduce AI-citation probability and how do they translate into score penalties?

## Detector battery → severity → negative SCORING contribution
**Path/Symbol:** `src/geo_optimizer/core/audit_negative.py:audit_negative_signals` (whole module 257L); penalties applied at `scoring.py:_penalty_negative_signals` (212–223); thresholds in `models/config.py` (503–513).
**Signature:** `audit_negative_signals(soup, raw_html, content, meta, schema) -> NegativeSignalsResult`.
**Data Shape:** flags incl. `cta_density_high`, `is_thin_content` (H1 promises depth but body < `MIXED_SIGNALS_WORD_THRESHOLD=1000`), `has_keyword_stuffing` (single-word density > `KEYWORD_STUFFING_THRESHOLD=0.025` per SEMrush 2025), `boilerplate_ratio > 0.6`, `has_mixed_signals` + detail; `checked` gates everything; severity high(4+)/medium(2–3)/low(1) map to −5/−3/−1.

### Decisive source
```python
# scoring.py — penalty enters the breakdown as a NEGATIVE category
if severity == "high":   return -NEGATIVE_PENALTY_HIGH    # −5
if severity == "medium": return -NEGATIVE_PENALTY_MED      # −3
if severity == "low":    return -NEGATIVE_PENALTY_LOW     # −1

# build_recommendations flips it back for ranking:
return -score_breakdown.get("negative_penalty", 0)   # magnitude = recoverable points
```

**Flow:** zero HTTP fetches; CTA density counts promo-link text patterns against word count; thin-content compares H1's promise words to body length; stuffing uses per-word density over cleaned text with a named worst offender (`stuffed_word`, `stuffed_density`) surfaced in recommendations; boilerplate ratio from non-main chrome text share.
**Invariant:** The unchecked result contributes ZERO (both `None` and `checked=False` guard) so opt-in absence never punishes a score; penalties live in ONE breakdown key consumed by scorer, recommendations (magnitude flip), and history persistence alike. Author-signal presence (`has_author_signal`) is collected here but CONSUMED by trust identity layer — cross-module reuse, not duplication.
**Probe:** `tests/test_negative_signals.py::test_severity_ladder_and_penalty_keys` (+ detector suites; `PYTHONPATH=src pytest tests/test_negative_signals.py -q` green at pin).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-aeo-geo-optimizer-skill", query: "negative signals penalty", limit: 5, fields: ["signature","name","file"] });
```

## Verdict
Adopt gated-detector battery + single-negative-breakdown-key for quality penalties; adapt thresholds/detectors; omit Italian text heuristics if your corpus is English-only.
