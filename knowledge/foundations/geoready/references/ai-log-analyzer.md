<!-- capsule-v2 -->
# AI log analyzer — combined/JSON log parsing into AI-crawler traffic stats with UA-fragment matching

**Source:** GeoReady (Geo Optimizer) MIT `main@a7165be2`; Codebase Memory `ext-aeo-geo-optimizer-skill`. **Question:** How do you detect which AI bots actually crawled a site from raw server logs?

## Dual-format line parser → bot attribution → per-bot/per-page aggregation
**Path/Symbol:** `src/geo_optimizer/core/log_analyzer.py:analyze_log_file` (33–81), `_parse_line` (84–105), `_match_bot` (125–132), `_aggregate_bots` (134+).
**Signature:** `analyze_log_file(file_path, *, max_lines=1_000_000) -> LogAnalysisResult`.
**Data Shape:** combined regex captures `(date, method, path, status, user-agent)`; JSON lines accept `user_agent|userAgent|http_user_agent`, `path|uri|url`, `timestamp|time|date` (CloudFront/Vercel shapes); output `BotStats(bot_name, visits, unique_pages, first_seen, last_seen)` + top pages with per-bot sets.

### Decisive source
```python
_COMBINED_RE = re.compile(
    r'^[\d.:a-fA-F]+\s+\S+\s+\S+\s+\[([^\]]+)\]\s+"(\S+)\s+(\S+)\s+[^"]*"\s+(\d+)\s+\S+\s+"[^"]*"\s+"([^"]*)"'
)
# lowercase UA fragments built ONCE from the config bot table — single source of truth
_BOT_UA_FRAGMENTS: dict[str, str] = {}
for bot_name in AI_BOTS:
    _BOT_UA_FRAGMENTS[bot_name.lower()] = bot_name

def _match_bot(ua: str) -> str | None:
    ua_lower = ua.lower()
    for fragment, name in _BOT_UA_FRAGMENTS.items():
        if fragment in ua_lower:
            return name
```

**Flow:** stream file line-by-line capped at max_lines (`errors="replace"` for hostile bytes) → try JSON when line starts `{`, else combined regex → substring UA match against the fragment map → group visits per bot → aggregate sorted by visit count; date range = min/max of bot-visit dates only.
**Invariant:** The bot table is IMPORTED from config, not duplicated — adding a bot to AI_BOTS automatically extends log detection; fragment matching (not equality) survives versioned UAs like `Mozilla/5.0 (compatible; PerplexityBot/1.0; ...)`. Unparseable lines are skipped silently but counted in total_lines so the report can show coverage.
**Probe:** `tests/test_log_analyzer.py::test_combined_and_json_formats_detected` (+ aggregation tests; `PYTHONPATH=src pytest tests/test_log_analyzer.py -q` green at pin).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-aeo-geo-optimizer-skill", query: "log analyzer bot match", limit: 5, fields: ["signature","name","file"] });
```

## Verdict
Adopt config-driven UA-fragment matching + dual-format tolerance for any crawler-analytics tool; adapt formats; omit JSON key variants you don't see in your logs.
