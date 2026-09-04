
`<!-- capsule-v2 -->`
# Company search vertical projection — how do I specialize the generic search kernel for one vertical with a URN gate and null-safe flattening?

**Source:** open-linkedin-api MIT `main@5feee360ec26719d07d5e67638045e751b48a74c`; Codebase Memory `open-linkedin-api`. **Question:** how does a vertical search reuse the blended search machinery while guaranteeing entity kind?

## Vertical over blended search
**Path/Symbol:** `linkedin.py:Linkedin.search_companies` (:457–491); kernel `Linkedin.search` (:203–303, see voyager-pagination).
**Signature:** `search_companies(keywords: Optional[List[str]] = None, **kwargs) -> List`.
**Data Shape:** wire filters `filters=List((key:resultType,value:List(COMPANIES)))` + `queryContext=List(spellCorrectionEnabled->true)`; blended hits carry a `trackingUrn`; projection emits flat dicts `{urn_id, name, headline, subline}`.

### Decisive source
```python
filters = ["(key:resultType,value:List(COMPANIES))"]
params = {"filters": "List({})".format(",".join(filters)),
          "queryContext": "List(spellCorrectionEnabled->true)"}
if keywords:
    params["keywords"] = keywords
data = self.search(params, **kwargs)              # SAME generic kernel
for item in data:
    if "company" not in item.get("trackingUrn"):
        continue                                  # kind gate AFTER the wire filter
    results.append(
        {
            "urn_id": get_id_from_urn(item.get("trackingUrn", None)),
            "name": (item.get("title") or {}).get("text", None),
            "headline": (item.get("primarySubtitle") or {}).get("text", None),
            "subline": (item.get("secondarySubtitle") or {}).get("text", None),
        }
    )
```
(Projection chains follow the pattern `(item.get("title") or {}).get("text", None)` for every nested key.)

**Flow:** build vertical filters in List() grammar → delegate to the GENERIC search kernel (paging, type-guards, wall) → re-filter hits client-side by trackingUrn substring → flatten nested subtitle/title objects into a flat row with null-safe accessors.
**Invariant:** vertical specialization happens at TWO layers — the wire resultType filter narrows candidates but does NOT guarantee kind (blended search can still leak non-company hits), so the `"company" not in trackingUrn` gate is mandatory BEFORE projecting. Flattening never trusts nesting: every optional object goes through `(x or {}).get(k)` so absent subtitles become None instead of AttributeError. urn_id derives from trackingUrn via the shared get_id_from_urn splitter.
**Probe:** no upstream tests (runner block recorded). Byte-exact grep resolves :466 (resultType filter) / :480 (trackingUrn gate) / :484 (urn_id projection):
```bash
grep -n 'resultType,value:List(COMPANIES)|trackingUrn' open_linkedin_api/linkedin.py | head -5
```

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "open-linkedin-api", query: "search_companies", limit: 5 });
```

## Verdict
Adopt two-layer vertical gating (wire filter + client-side URN-kind check) and the null-safe flatten for any blended-search specialization; adapt the facet vocabulary per generation (voyager-search-facet-encoding holds the people/jobs counterparts); omit keyword pass-through defaults. Caveat: source-grounded only.
