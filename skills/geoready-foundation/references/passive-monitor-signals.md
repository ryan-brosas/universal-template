<!-- capsule-v2 -->
# Passive visibility monitor — seven weighted signals from one audit plus history momentum

**Source:** GeoReady (Geo Optimizer) MIT `main@a7165be2`; Codebase Memory `ext-aeo-geo-optimizer-skill`. **Question:** How do you build a 0–100 AI-visibility score from an existing audit without re-crawling?

## Signal objects scaled from audit fields + honest unknown-momentum
**Path/Symbol:** `src/geo_optimizer/core/monitor.py:run_passive_monitor` (35–53), signal builders (89–265), `_monitor_band` (303–308).
**Signature:** `run_passive_monitor(domain, use_cache=False, project_config=None, save_history=True, retention_days=90, history_db=None) -> MonitorResult`.
**Data Shape:** `MonitorSignal(key, label, score, max_score, status ∈ {strong, partial, missing, stable, weak, unknown}, details{})`; weights in config `MONITOR_SCORING` (citation_bot 20, user_fetch 10, llms 15, ai_discovery 15, entity 15, trust 15, momentum 10 = 100).

### Decisive source
```python
allowed = sorted(set(audit_result.robots.bots_allowed) & set(CITATION_BOTS))
score = round(max_score * (len(allowed) / max(1, len(CITATION_BOTS))))   # proportional fill
status = "strong" if len(allowed) == len(CITATION_BOTS) else "partial" if allowed else "missing"
...
# momentum with NO history is "unknown", not zero — honest absence:
if history_result is None or history_result.total_snapshots == 0:
    return MonitorSignal(key="momentum", ..., score=max_score // 2,
                         status="unknown", details={"reason": "no_history"})
```

**Flow:** domain normalized to scheme://host → one `run_full_audit` → HistoryStore save + trend read → seven signals: citation-bot access ∩ CITATION_BOTS (5 bots), user-tier fetch bots, llms.txt readiness (found 7 + h1/blockquote 3 + sections 3 + links 2), AI-discovery endpoint count /4, entity strength rescaled from the audit's brand_entity breakdown against `_MAX_BRAND_SCORE`, trust composite /25, momentum banded by score delta (≥5 full, >0 →8, 0 →6/stable, >−5 →3, else 1) → visibility sum + band (`MONITOR_BANDS` strong≥80/visible≥60/emerging≥35) → recommendations keyed off non-strong signals then audit recommendations capped at 5 total.
**Invariant:** Proportional-rescale pattern (`round(max * have/all)`) keeps each signal comparable when bot lists grow; the unknown-momentum mid-score preserves ranking sanity on first run while STATUS still tells the truth; monitor weights live ONLY in config like SCORING.
**Probe:** `tests/test_monitor.py::test_momentum_unknown_without_history` (+ per-signal suites; `PYTHONPATH=src pytest tests/test_monitor.py -q` green at pin).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-aeo-geo-optimizer-skill", query: "run_passive_monitor momentum", limit: 5, fields: ["signature","name","file"] });
```

## Verdict
Adopt derived-signal dashboards over a single audit + honest-unknown semantics; adapt signal set/weights; omit the GEO-specific recommendation copy.
