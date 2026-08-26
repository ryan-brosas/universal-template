<!-- capsule-v2 -->
# Profiled keyword expansion — how do you generate GEO keyword packs that survive an LLM outage?

**Source:** GEOrank (aeo-georank) Apache-2.0 `main@424a0cf92b37ad63c94ae9dc6f39745189ab7c94`; Codebase Memory `ext-aeo-georank`. **Question:** What architecture produces 8-dimension × 10-keyword packs with stable scores, business-profile awareness, and a deterministic fallback?

## Profile inference → AI JSON → sanitize-or-template
**Path/Symbol:** `backend/app/services/keyword_expansion.py` whole (431L): `DIMENSIONS` :16–28, `PROFILE_LIBRARY` :31–119 (5 profiles), `PROFILE_RULES` :121–127, `normalize_seeds` :131–143, `_stable_score` :145–148, `_infer_keyword_profile` :150–172, `_fallback_expand` :231–253, `_sanitize_dimension_items` :255–283, `_ai_expand` :286–336, `expand_keywords_with_status` :390–424.
**Signature:** `expand_keywords_with_status(seeds: list[str], provider_override=None) -> tuple[dict, bool]` — payload + provider_succeeded flag.
**Data Shape:** Dimensions fixed: semantic/scenario/commercial/ranking/review/brand/question/technical. Item: `{keyword ≤80 chars, recommendation_score 35..99, business_score 35..99, reason | None}`.

### Decisive source
```python
def _stable_score(seed, dimension_key, keyword, base, spread):
    digest = hashlib.md5(f"{seed}|{dimension_key}|{keyword}".encode()).hexdigest()
    return max(35, min(99, base + (int(digest[:8], 16) % spread)))   # deterministic per (seed,dim,kw)

# profile = argmax marker-count; zero markers ⇒ enterprise_service default
profile_key = max(scores.items(), key=lambda item: item[1])[0]
if scores[profile_key] == 0:
    profile_key = "enterprise_service"
```
```python
try:
    dimensions = await asyncio.wait_for(_ai_expand(...), timeout=8.0)
except Exception:
    if provider_override is not None:
        raise                      # BYOK users get their OWN failure, never silent fallback
    provider_succeeded = False
    dimensions = _fallback_expand(normalized, profile)
```
Sanitizer clamps AI scores into the same band and fills missing ones from the SAME hash function — so mixed AI/fallback packs stay comparable.

**Flow:** normalize seeds (trim/dedupe/cap 8×40chars) → infer one of 5 business profiles by keyword-marker voting → AI call (8s timeout) returns strict-JSON dimension packs → per-dimension sanitize (whitespace collapse, blocked_terms filter, score clamp/fill, dedupe, cap 10) with per-dimension template fallback → summary aggregates averages + ≥80 ratios. Template expansion `{s}` substitution over curated zh phrase grammar per profile × dimension.
**Invariant:** Output SHAPE is identical for AI and fallback paths (`provider_succeeded` flag aside); scores are stable across identical requests (hash-derived), enabling diffable snapshots in tests; BYOK requests NEVER silently downgrade to templates.
**Probe:** `backend/tests/test_keywords.py::KeywordExpansionServiceTests::test_expand_keywords_uses_ai_json_payload` + fallback tests (mocked AI payload round-trip; template path assertions).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-aeo-georank", query: "expand_keywords_with_status", limit: 5 });
// verified line-exact: keyword_expansion.py :390–424
```

## Verdict
Adopt profile+template+deterministic-score structure for any generative feature needing offline parity; adapt PROFILE_LIBRARY dictionaries to your domain; omit nothing else. Direct tests green under real runner.
