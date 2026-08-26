<!-- capsule-v2 -->
# ICP seed & anchors — what should an LLM write at cold start: a query or words worth trying?

**Source:** OpenOutreach GPL-3.0 `main@c3ac1434118ac5301b193506d1d01e6e313bc622`; Codebase Memory `openoutreach`. **Question:** How do you turn product docs + a target description into (a) opening search keywords and (b) synthetic positive profiles, with typed LLM output?

## Connected graph-selected seam
**Path/Symbol:** `openoutreach/core/pipeline/icp.py:ICPSpec` (:53-93), `_seed_keywords` (:108-128), `generate_seed` (:131-187), `generate_anchors` (:204-238), `ensure_anchors` (:249-293).
**Signature:** `generate_seed(campaign) -> list[(field, token)]`; `generate_anchors(campaign, count=ANCHOR_COUNT, existing=()) -> list[str]` (`[]` on outage); `ensure_anchors(campaign) -> np.ndarray | None`.
**Data Shape:** `ICPSpec{role_keywords[], domain_keywords[], seniority: Seniority|None (Literal-typed), location, headcount_min/max, country_code}`; ANCHOR_COUNT = 3; anchors persisted as `anchor_profiles: list[str]` + `anchor_embeddings: float32 bytes`.

### Decisive source
```python
_SEED_FIELDS = (("lead_job_title", "role_keywords"),
                ("lead_job_title", "domain_keywords"),   # domain words ride the TITLE axis:
                                                         # lead_industry is INERT (nonsense value
                                                         # returns the identical count), but
                                                         # lead_job_title matches headline text too
                ("lead_seniority", "seniority"),
                ("lead_location", "location"))

def _seed_keywords(spec):
    keywords = set()
    for field, attr in _SEED_FIELDS:
        values = getattr(spec, attr)
        values = values if isinstance(values, list) else [values]
        for item in values:
            if item:
                keywords |= {(field, token) for token in tokenize(str(item))}
    return sorted(keywords)          # EVERYTHING split into words — "Head of Growth" would
                                     # be three ANDed tokens, empty before learning starts
```

**Flow:** generate_seed is the ONLY LLM call discovery makes about queries (no qualified profiles exist yet to count) → keywords + headcount band + country land on the campaign → afterwards growth is pure counting (vocabulary.refresh). Anchors: generate → dedupe against existing → embed WITHOUT query terms → persist; later boots restore the stored set.
**Invariant:** The seed is a *vocabulary*, not a query — the walk conjoins tokens itself against measured feedback, so the LLM should emit "words worth trying" and as many as the ICP implies; one maximal query was the clause-model era's shape. Anchors are embedded without the seed's keywords because they are a claim about what a good *lead* looks like, not about which query to run — folding them in would have discovery score the seed highly on the strength of its own guess. Anchor generation is best-effort by design (failure leaves the campaign unanchored, never propagates); once any real lead qualifies, the stored set is permanent and never re-invented (a restart re-anchoring slightly differently would silently move the GP's positive region). Temperature differs by job: 0.3 for the seed (single most likely conjunction-ish words), 0.8 for anchors (spread across the ideal region).
**Probe:** `tests/test_anchors.py::TestEnsureAnchors` (:61-93), `TestAnchorFillUp` (:94-158), `TestAnchorLifecycle` (:159+); `tests/test_discovery.py::TestSeedKeywords` (:229+).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openoutreach", query: "generate_seed", limit: 5 });
```

## Verdict
Adopt: LLM writes structured word lists into a pydantic model with provider-vocabulary-typed fields (invalid seniority = wasted fetch, so it is Literal-enforced, not prompt-guided); word-splitting before anything becomes a query; anchors-as-profiles embedded in the candidate space, persisted, and frozen after first real acceptance. Adapt ICPSpec fields to your provider's axes; omit the jinja prompt templates' wording.
