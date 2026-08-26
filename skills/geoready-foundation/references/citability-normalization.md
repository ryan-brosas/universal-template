<!-- capsule-v2 -->
# Citability 47-method engine — how do you merge 47 heterogeneous detectors into one scale that survives new methods?

**Source:** GeoReady (Geo Optimizer) MIT `main@a7165be2`; Codebase Memory `ext-aeo-geo-optimizer-skill`. **Question:** How is a multi-method rubric scored so adding check #48 cannot silently reshape the 0–100 scale?

## Raw-over-max normalization + per-method MethodScore ledger
**Path/Symbol:** `src/geo_optimizer/core/citability.py:audit_citability` (3592–3697), `_compute_grade` (3577–3590).
**Signature:** `audit_citability(soup, base_url, soup_clean=None) -> CitabilityResult`.
**Data Shape:** each detector returns `MethodScore(name, detected, score, max_score)`; result carries `methods[47]`, `raw_score`, `max_possible`, `total_score 0–100 = round(100*raw/max)`, `grade` (same bands as SCORE_BANDS: ≥86/≥68/≥36), `top_improvements[:3]`.

### Decisive source
```python
raw = sum(m.score for m in methods)
max_possible = sum(m.max_score for m in methods)
total = round(100 * raw / max_possible) if max_possible else 0
# gap #4.16.3: the 47 methods add up to well over 100 raw points, so CLAMPING the
# sum at 100 made the top of the scale reachable roughly halfway through — a page
# could score "excellent" while a third of the methods sat at zero. Normalize
# against the maximum the methods themselves expose, derived from the methods list.
```

**Flow:** one shared `clean_text` via `_get_clean_text(soup, soup_clean)` (deepcopy + strip script/style/nav/footer/header — never re-parse) → run detectors in a fixed ordered list spanning Princeton GEO (+27% quotes, +41%…), AutoGEO answer-first, passage density, readability (Flesch-Kincaid constants from config), E-E-A-T composite, RAG readiness (answer capsule, token efficiency, entity resolution, KG density, retrieval triggers) → improvements = first 3 UNdetected methods in `_METHOD_ORDER` by impact, with keyword-stuffing warning force-inserted at head when detected.
**Invariant:** The method LIST is the source of truth for both score and max — no hardcoded 100 anywhere; `_get_clean_text` must reuse the caller's pre-cleaned soup (perf contract with the orchestrator's #285 optimization); grade thresholds duplicated in `_compute_grade` must track config SCORE_BANDS. Detectors are pure functions of (soup, clean_text, base_url) — no I/O — keeping the whole engine testable offline.
**Probe:** `tests/test_citability.py` (233-test module incl per-method fixtures; `PYTHONPATH=src pytest tests/test_citability.py -q` green at pin).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-aeo-geo-optimizer-skill", query: "audit_citability methods normalization", limit: 5, fields: ["signature","name","file"] });
```

## Verdict
Adopt raw/max normalization and the ordered-method-ledger shape for ANY multi-heuristic scorer; adapt the method set to your domain; omit the GEO-research impact percentages if your weights differ.
