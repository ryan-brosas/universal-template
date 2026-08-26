<!-- capsule-v2 -->
# Lead score bands — what makes a scraped lead worth 0–100, and why is the follower band a sales thesis, not math?

**Source:** Scout MIT `main@171503bf`; Codebase Memory `Scout`. **Question:** What are the exact additive components of `_calculate_lead_score`, and which band boundary would a porter silently break?

## Additive 100-capped checklist with one asymmetric follower ladder
**Path/Symbol:** `app/scrapers/enrichment.py:LeadEnricher._calculate_lead_score` (:535-564); called exactly once at :136 (`enriched['lead_score'] = self._calculate_lead_score(enriched)`), after the email/phone fields are final.
**Signature:** `_calculate_lead_score(lead_data: Dict) -> int` (0–100, `min(score, 100)`).
**Data Shape:** reads six keys off the enriched dict — `email` (+30) and `email_source == 'hunter.io'` (+5), `phone` (+30), `is_verified` (+10), `follower_count` (banded +15/+10/+5), `website` (+10), bio keyword hit (+5).

### Decisive source
```python
if lead_data.get('email'):
    score += 30
    if lead_data.get('email_source') == 'hunter.io':   # paid-source bonus rides
        score += 5                                     # INSIDE the email branch

followers = lead_data.get('follower_count', 0)
if 5000 <= followers <= 50000:        score += 15      # BOTH ends INCLUSIVE
elif 1000 <= followers <= 100000:     score += 10
elif followers > 0:                   score += 5       # any nonzero residue
# 0 followers scores NOTHING here — but profile-contract's validity gate
# treats 0 as authentic; these two planes deliberately disagree.

bio = (lead_data.get('bio') or '').lower()
keywords = ['coach', 'consultant', 'ceo', 'founder', 'entrepreneur',
             'agency', 'business', 'owner', 'director', 'manager']
```

**Flow:** pure function over the already-enriched dict — no I/O, no verification, just arithmetic over what discovery produced. Max reachable = 30+5+30+10+15+10+5 = **105**, clamped to 100 by the `min` cap (the cap is load-bearing, not cosmetic).
**Invariant:** the micro-influencer band `[5000, 50000]` is closed on both ends and OUTRANKS the wider `[1000, 100000]` band that fully contains it — port it as an opinionated sales thesis (small-but-real audiences beat celebrity reach), never "simplify" it to disjoint ranges or open intervals. The hunter bonus nests inside the email branch so a lead with a hunter-sourced email gets 35 total, but `email_source='hunter.io'` alone contributes nothing. Missing keys default through `.get()` everywhere — absence scores zero without raising. The bio keyword list is plain substring matching on lowercased text (`'agency'` hits inside `'agencies'`).
**Probe:** no direct test (zero-test repo). Deterministic probes: `grep -cF '5000 <= followers <= 50000' app/scrapers/enrichment.py` → **1**; `grep -cF 'min(score, 100)' app/scrapers/enrichment.py` → **2** (score cap :372 in `_score_and_verify_email` + lead-score cap :564); `grep -cF '_calculate_lead_score(enriched)' app/scrapers/enrichment.py` → **1** (:136).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "Scout", query: "calculate lead score followers", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the additive-cap shape and the inclusive overlapping-band ladder as-is (both boundaries are behavior); adapt weights/keywords/band edges per market thesis; omit nothing structural — but record that this is opinionated config masquerading as scoring, and that candidate-funnel owns `_score_and_verify_email` (:340-376) while THIS capsule owns only the post-discovery lead ranking.
