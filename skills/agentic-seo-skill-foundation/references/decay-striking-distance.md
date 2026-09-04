<!-- capsule-v2 -->
# decay + striking-distance detector — how do you find dying pages and winnable keywords from a GSC CSV?

**Source:** Agentic-SEO-Skill MIT `main@69199160`; Codebase Memory `ext-aeo-agentic-seo-skill`. **Question:** How is the before/after split chosen, and what makes a keyword "striking distance"?

## Period-split rank tracker
**Path/Symbol:** `scripts/content_decay_detector.py:detect_decay` (:42-105), `_read_rows` (:27-40), `_parse_date` (:19-26).
**Signature:** `detect_decay(path, args, split_date: date | None = None, decline_threshold: float = 0.2, min_impressions: float = 100.0) -> dict`.
**Data Shape:** `{rows, split_date, declining_pages[{url, previous/recent_clicks, click_drop_pct, impressions}], striking_distance_keywords(≤200)[{url, query, recent_impressions, avg_position, recent_clicks}], issues}`; CSV columns resolved via configurable names with fallbacks (`page`/`landing page`, `keyword`).

### Decisive source
```python
if split_date is None and dated_rows:
    dates = sorted(row["date"] for row in dated_rows)
    split_date = dates[len(dates) // 2]
...
avg_position = sum(row["position"] * row["impressions"] for row in query_rows) / max(1.0, impressions)
if 4.0 <= avg_position <= 20.0:
    striking_distance.append(...)
```

**Flow:** read CSV (utf-8-sig, headers lowercased/stripped) → undated rows default to the "recent" bucket (both assignment sites) → auto-split = MEDIAN date of dated rows when not supplied → per-URL click-drop ≥ threshold (default 20%) AND max-period impressions ≥ floor ⇒ declining page → per-query impression-weighted average position within [4.0, 20.0] and impressions ≥ floor ⇒ striking-distance keyword → declining sorted by drop% desc; striking by (position asc, impressions desc), capped at 200.
**Invariant:** Weighted average position is load-bearing — an unweighted mean over sparse days would rank keywords on quiet low-impression rows. Median split guarantees roughly balanced periods even for irregular exports; rows lacking dates are never evidence of decline but still count toward "recent" sums.
**Probe:** `grep -cF 'dates[len(dates) // 2]' scripts/content_decay_detector.py` (= 1); `grep -cF '4.0 <= avg_position <= 20.0' scripts/content_decay_detector.py` (= 1); `grep -cF 'striking_distance[:200]' scripts/content_decay_detector.py` (= 1); direct test `tests/test_content_ai_scripts.py::test_topical_cluster_mapper_and_decay_detector` asserts both `declining_pages` and `striking_distance_keywords` non-empty.
**Retrieve:** `codebase-memory-mcp cli search_graph '{"project":"ext-aeo-agentic-seo-skill","query":"decay striking distance position","limit":5}'`.

## Verdict
Adopt median-split period comparison + weighted-position window as the minimal rank-tracker kernel; adapt thresholds (0.2/100/[4,20]) to traffic scale; omit CSV plumbing if you consume GSC API directly. Probes executed green @69199160; fixture test green in the 34/34 run.
