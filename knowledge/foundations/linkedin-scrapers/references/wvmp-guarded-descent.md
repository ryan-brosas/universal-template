<!-- capsule-v2 -->
# Wvmp guarded descent — How do I extract a scalar through deeply nested $type-keyed envelopes without inheriting KeyError fragility?

**Source:** open-linkedin-api MIT `main@5feee360ec26`; Codebase Memory `open-linkedin-api`. **Question:** The original walks seven fixed keys/array indices into a profile-views envelope with zero guards — what is the safe porting contract?

## Brittle fixed-key descent as the negative template
**Path/Symbol:** `open_linkedin_api/linkedin.py:Linkedin.get_current_profile_views` (:1114–1130).
**Signature:** `get_current_profile_views() -> int` (the `numViews` scalar; raises KeyError on any shape drift).
**Data Shape:** `data["elements"][0]["value"]["com.linkedin.voyager.identity.me.wvmpOverview.WvmpViewersCard"]["insightCards"][0]["value"]["com.linkedin.voyager.identity.me.wvmpOverview.WvmpSummaryInsightCard"]["numViews"]` — two `$type`-keyed map lookups interleaved with two `[0]` array takes, then a leaf key. Every hop is mandatory; the endpoint `/identity/wvmpCards` returns whatever card set the server currently projects.

### Decisive source
```python
# :1120–1130, verbatim including the absence of ANY guard
        res = self._fetch(f"/identity/wvmpCards")

        data = res.json()

        return data["elements"][0]["value"][
            "com.linkedin.voyager.identity.me.wvmpOverview.WvmpViewersCard"
        ]["insightCards"][0]["value"][
            "com.linkedin.voyager.identity.me.wvmpOverview.WvmpSummaryInsightCard"
        ][
            "numViews"
        ]
```

**Flow:** GET wvmpCards → parse → descend elements→card value→insightCards→summary value→numViews.
**Invariant (porting):** every hop in a `$type`-keyed descent is nullable — server projections rotate type strings exactly like decorationIds (see decoration-id-response-shaping) and insight cards are an unordered list where index 0 may not exist. Port as: walk with `.get()` per map hop + length/isinstance check per array take + versionable constants for each `$type` string + explicit None/sentinel on first miss. Do NOT copy the chain verbatim; copy the PATH it documents (which two cards compose the summary) and guard it.
**Probe:** no upstream tests exist — source-grounded grep at HEAD: `wvmpCards` ⇒ :1120; `WvmpViewersCard` ⇒ :1125; `WvmpSummaryInsightCard` ⇒ :1127; `numViews` ⇒ :1129; the descent spans exactly :1124–1130.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "open-linkedin-api", query: "profile view statistics chart data", limit: 10, fields: ["signature", "lines"] });
// resolves Linkedin.get_current_profile_views :1114–1130 (observed this pass)
```

## Verdict
Adopt the guarded-descent discipline and treat this method as the canonical negative example inside the repo. Adapt hop-by-hop to your envelope's actual `$type` vocabulary at runtime, not to these pinned literals. Omit direct reuse of the unguarded expression. Pair with company-search-vertical-projection's null-safe flattening (same failure class, defensive twin already mined). Coverage caveat: no upstream tests; coverage check on linkedin.py = no_recorded_issue + metadata_match (best-effort signal).
