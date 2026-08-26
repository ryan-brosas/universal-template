<!-- capsule-v2 -->
# robots longest-match evaluator — how do you decide allow vs disallow the way crawlers do?

**Source:** Agentic-SEO-Skill MIT `main@69199160`; Codebase Memory `ext-aeo-agentic-seo-skill`. **Question:** When both an Allow and a Disallow rule match a path, which wins and why does the sort key matter byte-for-byte?

## Group parser + longest-match resolver
**Path/Symbol:** `scripts/seo_common.py:parse_robots_txt` (:263-291), `_robots_pattern_to_regex` (:294-298), `robots_allowed` (:301-320).
**Signature:** `robots_allowed(parsed_robots: dict | None, url: str, user_agent: str = "*") -> tuple[bool, str]`.
**Data Shape:** `parsed_robots = {"groups": [{"agents": [...], "rules": [("allow"|"disallow", pattern)]}], "sitemaps": [...], "crawl_delays": {agent: float}}`; returns `(allowed, "directive: pattern")` with human-readable evidence.

### Decisive source
```python
matches.sort(key=lambda item: (item[0], item[1] == "allow"), reverse=True)
_, directive, pattern = matches[0]
return directive == "allow", f"{directive}: {pattern}"
```

**Flow:** group parser opens a new group when `user-agent:` follows a group that already has rules (agents accumulate within a rules-less prefix) → matcher collects every rule whose group's agents contain `"*"` or overlap the UA bidirectionally (`agent in ua or ua in agent`) → empty `Disallow:` (full allow) is skipped, not treated as match-all → patterns compile with `*`→`.*`, trailing-`$` restored after escaping → longest pattern wins; EQUAL lengths resolve to **allow** because `(len, directive=="allow")` sorts True-above-False under reverse.
**Invariant:** Tie-break polarity is load-bearing — flipping the boolean flips equal-length outcomes. The empty-disallow skip is equally load-bearing: without it `Disallow:` would regex-match everything.
**Probe:** `grep -c 'matches.sort(key=lambda item: (item\[0\], item\[1\] == "allow"), reverse=True)' scripts/seo_common.py` (= 1); `grep -c 'pattern == ""' scripts/seo_common.py` (= 1).
**Retrieve:** `codebase-memory-mcp cli search_graph '{"project":"ext-aeo-agentic-seo-skill","query":"robots_allowed parse_robots_txt crawl","limit":5}'`.

## Verdict
Adopt the longest-match-with-allow-tiebreak evaluator for any robots decision logic; adapt the bidirectional UA substring matching if your consumers need strict per-UA semantics; omit `crawl_delays` enforcement (parsed but never enforced anywhere). Probe executed green @69199160; upstream coverage via `tests/test_core_seo_scripts.py` suite green 34/34.
