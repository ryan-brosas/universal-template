<!-- capsule-v2 -->
# title/slug recommendation — how do you derive a recommended repo slug and display title from metadata with zero keyword API?

**Source:** Agentic-SEO-Skill MIT `main@69199160`; Codebase Memory `aeo-agentic-seo-skill`. **Question:** What seed order and promotion rules turn name/topics/description into a deterministic slug + title, and which tokens get special treatment?

## Intent-seeded keyword ladder with forced-"seo" promotion
**Path/Symbol:** `scripts/github_repo_audit.py:analyze_title_strategy` (:136-192), helpers `_tokenize` (:116-119), `_dedupe_keep_order` (:121-129), `_format_title_token` (:131-134), module `STOP_WORDS` (:30-36). Called from `build_audit` at :284 as `report["title_analysis"]`.
**Signature:** `analyze_title_strategy(repo_slug: str, metadata: dict) -> dict`.
**Data Shape:** Input: slug `owner/repo` + API metadata dict (`name`, `description`, `topics[]`). Output keys: `current_name`, `current_has_underscore`, `current_has_hyphen`, `search_intent_keywords` (≤12), `recommended_repo_slug`, `recommended_display_title`, `alternative_titles` (≤3), `notes` (3 fixed disclaimer strings). Pure function — no I/O, no network.

### Decisive source
```python
priority_seed = name_tokens + topic_tokens + desc_priority          # :154
keywords = _dedupe_keep_order(priority_seed)
if not keywords:
    keywords = _tokenize(repo_slug.replace("/", " "))               # :157-158
slug_tokens = keywords[:5] if keywords else []
if "seo" in keywords and "seo" not in slug_tokens:
    slug_tokens = ["seo"] + slug_tokens[:4]                         # :161-162
...
for token in slug_tokens:
    if token in ("for", "and", "the"):                              # :168
        continue
display_title = " ".join(_format_title_token(t) for t in title_tokens[:7]).strip()  # :172
```

**Flow:** tokenize name (`_`/`-`→space), each topic, and description separately → description words ranked by `Counter.most_common(15)` → concatenate in fixed priority order name → topics → description-top-15 → order-preserving dedupe → empty fallback tokenizes the slug itself → first 5 keywords become slug candidates; if `seo` appears anywhere in keywords but missed the top 5, it is force-promoted to position 0 (pushing the list to 4 others) → slug = hyphen-joined tokens, else lowercased underscore-swapped repo name → title drops only `for`/`and`/`the` from the slug tokens, caps at 7 tokens, maps acronyms via `_format_title_token` (`seo→SEO, llm→LLM, ai→AI, api→API, github→GitHub, aeo→AEO, geo→GEO`, else `.capitalize()`).
**Invariant:** Seed ORDER is the contract — name beats topics beats description frequency; dedupe keeps first occurrence so a name token always outranks a same-word topic/description token. The forced-"seo" rule exists because SEO repos whose top-5 intent words exclude "seo" would otherwise lose their single most searchable term from the slug. Title capitalization must go through the acronym map or ports emit "Seo"/"Llm". The three `notes` strings are part of the output contract: they label the result as an intent heuristic that still needs keyword-volume validation.
**Probe:** no direct upstream unit test covers this function (the `build_audit` network path is untested — standing caveat); content pins executed at pin: `most_common(15)` :152 ×1, `priority_seed = ` :154 ×1, `"seo" in keywords` :161 ×1, `slug_tokens = ["seo"]` :162 ×1, `("for", "and", "the")` :168 ×1, `title_tokens[:7]` :172 ×1, call site :284 ×1; full suite 34 passed (`PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider`).

## Get live surrounding code
**Retrieve:**
```json
{"tool":"mcp__codebase-memory__search_graph","args":{"project":"aeo-agentic-seo-skill","query":"analyze_title_strategy keyword seeding slug recommendation","limit":5}}
```
Not executed this pass — Codebase Memory MCP surface absent in the pass-3 session; seam selected and confirmed by direct read at pin (recorded in verification.md). Execute on revalidation.

## Verdict
Adopt the ordered-seed + first-occurrence-dedupe shape and the forced-promotion slot verbatim for any "recommend identifier from mixed metadata" problem (rename it to your domain's magic term). Adapt the STOP_WORDS set, the acronym map, and the top-15/top-5/top-7 cutoffs to your corpus; omit nothing structural — the function is pure and dependency-free, so it ports as-is. Coverage caveat: heuristic thresholds (15/5/7, stopword drop list) are content-pinned, not test-pinned.
