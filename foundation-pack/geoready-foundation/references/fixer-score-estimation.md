<!-- capsule-v2 -->
# Fixer & score estimation — generated remediations whose promised points are computed, not guessed

**Source:** GeoReady (Geo Optimizer) MIT `main@a7165be2`; Codebase Memory `ext-aeo-geo-optimizer-skill`. **Question:** How does an auto-fixer produce robots/llms/schema/meta patches AND an honest post-fix score estimate?

## Category fix generators + delta-from-CATEGORY_MAX estimator
**Path/Symbol:** `src/geo_optimizer/core/fixer.py:generate_robots_fix` (28–98), `_estimate_score_after` (419–495), `run_all_fixes` (497+).
**Signature:** `generate_robots_fix(result, base_url, project_config=None) -> FixItem | None`; `_estimate_score_after(result, fixes) -> int`; `run_all_fixes(url, audit_result=None, only=None, project_config=None) -> FixPlan`.
**Data Shape:** `FixItem(category, description, content, file_name, action ∈ {create, append, overwrite})`; robots fix merges `project_config.extra_bots` into AI_BOTS exactly as the auditor did (#120/#422 symmetry).

### Decisive source
```python
if "robots" in categories_fixed:
    max_robots = SCORING["robots_found"] + SCORING["robots_citation_ok"]   # 18 — inline, no core→cli import
    current_robots = 0
    if result.robots.found:
        current_robots = SCORING["robots_found"]
        if result.robots.citation_bots_ok:
            current_robots += (SCORING["robots_citation_ok"]
                               if result.robots.citation_bots_explicit else ROBOTS_PARTIAL_SCORE)
        elif result.robots.bots_allowed:
            current_robots += ROBOTS_PARTIAL_SCORE
    bonus += max_robots - current_robots
...
return min(100, result.score + bonus)
```

**Flow:** no robots.txt → full-file create (User-agent: * Allow + per-bot blocks + Sitemap line); exists-but-incomplete → APPEND block covering `bots_missing + bots_blocked` (#211: a Disallow'd bot still needs its Allow rule); llms → regenerate from sitemap when incomplete; schema/meta/AI-discovery → targeted templates; content → rewrite suggestion; estimate walks ONLY the fixed categories mirroring the scorer's exact branch logic and clamps at 100.
**Invariant:** The estimator MUST duplicate scoring.py's branch semantics (explicit-vs-wildcard robots distinction included) or promised deltas lie; every generator returns `None` when nothing is needed so the plan contains only actionable items; extra_bots handling mirrors run_full_audit or generated files would omit configured bots.
**Probe:** `tests/test_fix.py::test_robots_fix_appends_blocked_bots` (+ estimator suites in `tests/test_cli.py` geo-fix tests; `PYTHONPATH=src pytest tests/test_fix.py -q` green at pin).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-aeo-geo-optimizer-skill", query: "_estimate_score_after generate_robots_fix", limit: 5, fields: ["signature","name","file"] });
```

## Verdict
Adopt computed-delta estimates tied to the same weight table as the scorer for any advisory fixer; adapt categories; omit content-rewrite generation if you don't produce copy.
