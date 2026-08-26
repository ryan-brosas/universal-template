<!-- capsule-v2 -->
# Profile me-card variant family — How do I read per-profile identity cards when default headers omit the normalized-JSON accept and each card needs its own fail-soft guard?

**Source:** open-linkedin-api MIT `main@5feee360ec26`; Codebase Memory `open-linkedin-api`. **Question:** How do I read per-profile identity cards (privacy settings, badges, network info) when the session's default headers do not request normalized JSON and each card must fail soft instead of raising?

## Identity-card read template (three endpoints, one shape)
**Path/Symbol:** `open_linkedin_api/linkedin.py:Linkedin.get_profile_privacy_settings` (:1493–1510), `Linkedin.get_profile_member_badges` (:1512–1529), `Linkedin.get_profile_network_info` (:1531–1555).
**Signature:** `get_profile_privacy_settings(public_profile_id: str) -> Dict` — identical arity for badges/network_info.
**Data Shape:** URI `/identity/profiles/{public_profile_id}/{privacySettings|memberBadges|networkinfo}`; explicit per-call `accept: application/vnd.linkedin.normalized+json+2.1` (the shared `Client.REQUEST_HEADERS` omits it — commented out at `client.py:35`, so nothing else in the session requests this projection); non-200 → `{}`; success unwraps `data.get("data", {})`. The normalized envelope's `included[]` plane is consumed server-side; the client never joins it.

### Decisive source
```python
# get_profile_network_info (:1547–1555); privacy/badges identical modulo resource suffix
        res = self._fetch(
            f"/identity/profiles/{public_profile_id}/networkinfo",
            headers={"accept": "application/vnd.linkedin.normalized+json+2.1"},
        )
        if res.status_code != 200:
            return {}

        data = res.json()
        return data.get("data", {})
```

**Flow:** build slug-addressed URI → override accept to the normalized projection → GET via `_fetch` → status gate returns `{}` on any non-200 → unwrap the `data` key of the normalized envelope.
**Invariant:** the three cards are one template; a port adds ONLY the resource suffix per card. Fail-soft `{}` never raises (transport auth exceptions excepted). Contrast: sibling reads in the same file do NOT follow it — `get_profile_skills` (:702–726, owned by voyager-graphql-queryid) skips the status guard AND mutates returned elements (`del item["entityUrn"]`), so the guard is a per-family decision, not a repo-wide one.
**Probe:** no upstream tests exist (repo ships none) — source-grounded grep at HEAD: `application/vnd.linkedin.normalized+json+2.1` resolves 9 call sites :632/:886/:1453/:1474/:1504/:1523/:1549/:1569/:1621; the three card guards sit at :1506–07/:1525–26/:1551–52; the three unwraps at :1510/:1529/:1555.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "open-linkedin-api", query: "profile privacy settings member badges network info", limit: 10, fields: ["signature", "lines"] });
// resolves Linkedin.get_profile_member_badges :1512–1529, get_profile_network_info :1531–1555,
// get_profile_privacy_settings :1493–1510 (observed this pass)
```

## Verdict
Adopt the card-template discipline: path-slug addressing + explicit projection accept + status-gated `{}` + single-key unwrap, parameterized only by resource suffix. Adapt the slug vocabulary (`public_profile_id` here vs `public_id`/`urn_id` elsewhere in the same class — normalize at YOUR boundary). Omit LinkedIn's field vocabularies inside each card. Coverage caveat: no upstream tests; `check_index_coverage` on linkedin.py = no_recorded_issue + metadata_match (best-effort signal).
