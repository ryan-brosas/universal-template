<!-- capsule-v2 -->
# entity sameAs KG-ladder — how do you audit an organization's Knowledge-Graph identity signals?

**Source:** Agentic-SEO-Skill MIT `main@69199160`; Codebase Memory `ext-aeo-agentic-seo-skill`. **Question:** Which entity types count, which platforms are ranked critical→weak, and what does "missing" mean?

## Platform-ranked identity audit
**Path/Symbol:** `scripts/entity_checker.py:SAMEAS_PLATFORMS` (:26-37), `extract_entities_from_schema` (:52-88), `analyze_sameas` (:93-171), `check_wikidata`/`check_wikipedia`/`check_google_knowledge_graph` (:177-272).
**Signature:** `analyze_sameas(same_as_list: list) -> {"found","missing","issues","total_found","total_missing_critical"}`.
**Data Shape:** SAMEAS_PLATFORMS maps domain → `{name, priority: Critical|High|Medium|Low, kg_signal: Primary|Strong|Moderate|Weak}`; missing = Critical+High platforms absent from found.

### Decisive source
```python
if schema_type in ("Organization", "Person", "Corporation",
                   "LocalBusiness", "Brand", "MedicalOrganization",
                   "EducationalOrganization", "GovernmentOrganization"):
...
for platform_domain, info in SAMEAS_PLATFORMS.items():
    if info["priority"] in ("Critical", "High"):
        if info["name"] not in found:
            missing[info["name"]] = {...}
```

**Flow:** JSON-LD extraction unwraps top-level arrays AND `@graph` containers → 8-type entity filter (the :287 NAP check re-matches only LocalBusiness/Organization of those) → sameAs strings/lists domain-normalized (`www.` stripped, substring platform match) → unmatched domains recorded as Low/Unknown → missing = every Critical (wikipedia.org, wikidata.org) + High (linkedin.com, twitter.com, x.com) platform not found → liveness spot-check via HEAD on FIRST 3 found URLs only (≥400 = Warning; unreachable = Info, never a crash) → optional Wikidata wbsearchentities (confidence High iff label case-insensitively equals query), Wikipedia titles API (`page_id != "-1"`), and GKG API gated on key presence.
**Invariant:** "total_missing_critical" actually counts Critical+HIGH — the field name undercounts its own semantics. Platform matching is substring-based, so a self-hosted `wiki.mysite.org` would false-match wikipedia.org — porter must anchor or reverse the containment for hostile input.
**Probe:** `grep -c '@graph' scripts/entity_checker.py` (= 3: docstring mention + unwrap + comment); unwrap gate `if "@graph" in data` (= 1); `("Critical", "High")` gate (= 1); 8-type tuple at :88.
**Retrieve:** `codebase-memory-mcp cli search_graph '{"project":"ext-aeo-agentic-seo-skill","query":"entity sameAs wikidata knowledge graph","limit":5}'`.

## Verdict
Adopt the priority-tiered platform roster and @graph-aware extraction; adapt the roster per market; fix the substring containment before reusing on untrusted input; omit live HEAD checks if offline. Probes executed green @69199160.
