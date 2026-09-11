<!-- capsule-v2 -->
# Bots config & 3-tier classification — which AI crawlers exist, which matter for citations, and the #512 corrections

**Source:** GeoReady (Geo Optimizer) MIT `main@a7165be2`; Codebase Memory `ext-aeo-geo-optimizer-skill`. **Question:** What bot vocabulary should a GEO tool track, and which vendor-documentation traps must it avoid?

## AI_BOTS dict → BOT_TIERS sets → CITATION_BOTS critical subset
**Path/Symbol:** `src/geo_optimizer/models/config.py:AI_BOTS` (65–114), `BOT_TIERS` (117–151), `CITATION_BOTS` (157).
**Signature:** module constants; consumers: robots audit (`bots=` param), monitor signals, log-analyzer UA fragments.
**Data Shape:** `AI_BOTS: {name: description}` (26 bots across OpenAI/Anthropic/Perplexity/Google/Microsoft/Apple/Meta/Amazon/xAI/You/Common Crawl); tiers `training` / `search` / `user`; `CITATION_BOTS = {OAI-SearchBot, Claude-SearchBot, PerplexityBot, Googlebot, Applebot}`.

### Decisive source
```python
# anthropic-ai/claude-web removed (#512): not listed in Anthropic's current
# published crawler docs (support.claude.com), which name exactly these three.
"ClaudeBot": "Anthropic (Claude training)",
...
# Googlebot (#512): the same crawler that feeds Search also feeds AI Overviews —
# Google's own docs state Google-Extended is a robots.txt token layered on
# Googlebot's data, NOT a separate fetching agent, and controls only Gemini/Vertex
# training, not AI Overviews eligibility.
"Googlebot": "Google (Search + AI Overviews)",
"Google-Extended": "Google (Gemini/Vertex training opt-out — not a crawler)",
...
# CITATION_BOTS (#512): matches the "AI search crawlers" set, not the training-only
# crawlers that happen to share a vendor. ClaudeBot is training-only per Anthropic's
# current docs, so it is excluded here even though it is Anthropic's bot.
```

**Flow:** robots audit checks each tracked name's Allow/Disallow; scoring awards explicit citation-bot permission over wildcard (`ROBOTS_PARTIAL_SCORE` distinction); monitor scales signal by `|allowed ∩ CITATION_BOTS| / |CITATION_BOTS|`; log analyzer lowercases the whole table into UA fragments. Display strings for user-facing recommendations are separate constants (`ROBOTS_KEY_BOTS_DISPLAY`) so message copy can stay short while the check set stays complete.
**Invariant:** Tier membership is semantic, not vendor-grouped — ClaudeBot is Anthropic but training-tier and thus EXCLUDED from citation scoring; Google-Extended appears in the table but is documented as an opt-out token, not a fetcher. A porter who treats "all big-vendor bots" as citation-critical mis-scores every site.
**Probe:** `tests/test_core.py::test_ai_bots_registry_shape` + tier-consistency asserts in `tests/test_monitor.py` (`PYTHONPATH=src pytest tests/test_core.py tests/test_monitor.py -q` green at pin).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-aeo-geo-optimizer-skill", query: "AI_BOTS BOT_TIERS citation", limit: 5, fields: ["signature","name","file"] });
```

## Verdict
Adopt the three-tier taxonomy + documentation-grounded citation subset; refresh names against vendor docs when you port (that IS the lesson of #512); omit deprecated tokens like `anthropic-ai/claude-web`.
