<!-- capsule-v2 -->
# Member-share feed scoping — How do I scope feed reads to ONE member across TWO endpoints, and which serialization quirks ride along?

**Source:** open-linkedin-api MIT `main@5feee360ec26`; Codebase Memory `open-linkedin-api`. **Question:** The same `q=memberShareFeed` scoping appears on two different endpoints with different identity params and paging machines — which variant applies when, and what must a porter flatten?

## memberShareFeed across /identity/profileUpdatesV2 and /feed/updates
**Path/Symbol:** `open_linkedin_api/linkedin.py:Linkedin.get_profile_posts` (:106–155) and `Linkedin.get_profile_updates` (:1065–1112).
**Signature:** `get_profile_posts(public_id=None, urn_id=None, post_count=10) -> List`; `get_profile_updates(public_id=None, urn_id=None, max_results=None, results=None)` (recursive).
**Data Shape:** BOTH scope by wire params, never by client-side filtering. Variant A (profileUpdatesV2): `q=memberShareFeed`, `moduleKey="member-shares:phone"` (:128), `includeLongTermHistory: True` (:129), identity via FULL URN — `profileUrn = urn:li:fsd_profile:{urn_id}` or rewritten from the fetched profile's `profile_urn` (`fs_miniProfile`→`fsd_profile`, :131–137); token-paged via `metadata.paginationToken`; embedded-status guard returns `[{}]` — a LIST-wrapped sentinel (:142–144). Variant B (/feed/updates): same q but `moduleKey="member-share"` (:1085), identity via bare scalar `profileId`, count `_MAX_UPDATE_COUNT`(100)/start accumulation; three-exit recursion: empty elements OR max_results reached OR ratio wall `len/max >= _MAX_REPEATED_REQUESTS(200)`. QUIRK: `profileId` is passed as a ONE-ELEMENT SET LITERAL `{public_id or urn_id}` (:1083), flattened only because requests' urlencode iterates set values (doseq); under a non-doseq serializer it would send the repr.

### Decisive source
```python
# get_profile_updates :1082–1090 (variant B params + quirk)
        params = {
            "profileId": {public_id or urn_id},
            "q": "memberShareFeed",
            "moduleKey": "member-share",
            "count": Linkedin._MAX_UPDATE_COUNT,
            "start": len(results),
        }

        res = self._fetch(f"/feed/updates", params=params)
```

**Flow:** resolve member identity → choose endpoint by need (posts surface + long-term history ⇒ profileUpdatesV2 with full fsd_profile URN and token paging; raw activity stream ⇒ /feed/updates with profileId and start-accumulation recursion) → loop until that variant's exit condition.
**Invariant:** scoping lives in the params (`q`+`moduleKey`+identity key), so ports must reproduce all three together — swapping `moduleKey` variants silently changes the projection ("member-shares:phone" ≠ "member-share"). Paging MACHINES themselves are owned by voyager-pagination; this capsule owns only the member-scoping layer above them. Flatten single-value collections explicitly when leaving requests' doseq world.
**Probe:** no upstream tests exist — source-grounded grep at HEAD: `"q": "memberShareFeed"` ⇒ :127 AND :1084; moduleKeys ⇒ :128 (`member-shares:phone`) and :1085 (`member-share`); set literal ⇒ :1083 exactly; `fs_miniProfile→fsd_profile` rewrite ⇒ :135–136; `[{}]` sentinel ⇒ :144; ratio wall ⇒ :1099.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "open-linkedin-api", query: "profile updates newsfeed activity member share feed", limit: 10, fields: ["signature", "lines"] });
// resolves Linkedin.get_profile_updates :1065–1112 (observed this pass);
// get_profile_posts :106–155 also matches the family
```

## Verdict
Adopt param-level vertical scoping with paired (endpoint, moduleKey, identity-key) triples kept atomic. Adapt the identity resolution: prefer full `fsd_profile` URNs on identity-plane endpoints and bare ids on feed-plane ones, mirroring the two variants. Omit the vendor-tuned constants (`_MAX_UPDATE_COUNT`, `_MAX_REPEATED_REQUESTS`) as portable values. Coverage caveat: no upstream tests; coverage check on linkedin.py = no_recorded_issue + metadata_match.
