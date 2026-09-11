<!-- capsule-v2 -->
# ai-crawler policy matrix — which AI user-agents must a site's robots/llms posture be audited for?

**Source:** Agentic-SEO-Skill MIT `main@69199160`; Codebase Memory `ext-aeo-agentic-seo-skill`. **Question:** What is the canonical AI-crawler roster and the three-state alignment classification per crawler?

## Roster × path decision grid
**Path/Symbol:** `scripts/ai_crawler_policy_matrix.py:matrix` (:16-40), `AI_CRAWLERS` (:13).
**Signature:** `matrix(site: str, paths: list[str] | None = None, timeout: int = 15) -> dict` (defaults paths `["/", "/llms.txt", "/sitemap.xml"]`).
**Data Shape:** `{site, robots_url, robots_status, llms_txt_url, llms_txt_status, rows: [{crawler, policy: allowed|restricted, paths: {path: {allowed, rule}}, llms_txt_available, alignment: documented|robots_only|allowed_without_llms_txt}]}`.

### Decisive source
```python
AI_CRAWLERS = ["GPTBot", "ChatGPT-User", "ClaudeBot", "PerplexityBot",
               "Google-Extended", "Applebot-Extended", "CCBot", "Bytespider", "Amazonbot"]
...
"alignment": "documented" if llms.get("status") == 200 and allowed_all
             else "robots_only" if not allowed_all else "allowed_without_llms_txt"
```

**Flow:** fetch robots.txt once + llms.txt once → per crawler evaluate `robots_allowed` at every requested path (longest-match evidence string carried per cell) → `allowed_all` ANDs across paths → alignment: fully allowed + live llms.txt = `documented`; any restriction = `robots_only` (regardless of llms.txt); fully allowed without manifest = `allowed_without_llms_txt`.
**Invariant:** The roster is a FROZEN AUDIT CONTRACT (9 UAs incl. ChatGPT-User distinct from GPTBot — training vs user-action traffic). `policy` is binary allowed/restricted; there is no partial state even when only one path is blocked.
**Probe:** roster size 9 via module import (`len(m.AI_CRAWLERS)` = 9); `grep -cF '"GPTBot"' scripts/ai_crawler_policy_matrix.py` (= 1); `grep -cF '"documented" if' scripts/ai_crawler_policy_matrix.py` (= 1).
**Retrieve:** `codebase-memory-mcp cli search_graph '{"project":"ext-aeo-agentic-seo-skill","query":"AI crawlers GPTBot ClaudeBot matrix","limit":5}'`.

## Verdict
Adopt the 9-UA roster as the audit baseline (extend with new bots upstream-first); adapt default probe paths to your sitemap layout; omit the alignment trichotomy if you only need raw decisions. Probes executed green @69199160.
