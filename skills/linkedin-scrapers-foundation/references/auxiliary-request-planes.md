<!-- capsule-v2 -->
# Auxiliary request planes — How do I call non-voyager planes (www-host telemetry POST, action-verb follow-state write) without breaking host/header conventions?

**Source:** open-linkedin-api MIT `main@5feee360ec26`; Codebase Memory `open-linkedin-api`. **Question:** How do I reach endpoints that live OUTSIDE the voyager API plane — a www-host telemetry beacon and an action-verb follow-state write — while keeping one transport pair?

## track() beacon on the bare host + unfollow action-verb write
**Path/Symbol:** `open_linkedin_api/linkedin.py:Linkedin.track` (:1479–1491), `Linkedin.unfollow_entity` (:1557–1577); mechanism `Linkedin._post` (:99–104) + hosts `Client.LINKEDIN_BASE_URL`/`API_BASE_URL` (`client.py:25–26`).
**Signature:** `track(eventBody, eventInfo) -> bool` (error state); `unfollow_entity(urn_id: str) -> bool`.
**Data Shape:** track wraps `{eventBody, eventInfo}`, JSON-stringifies it, but sends it with `content-type: text/plain;charset=UTF-8` and `accept: */*` — beacon-style JSON-under-text-plain. Its URI `/li/track` is joined to the BARE www host because `base_request=True`. unfollow_entity stays on the API plane: noun resource `/feed/follows` + verb in the query string `?action=unfollowByEntityUrn`, payload `{"urn": "urn:li:fs_followingInfo:{urn_id}"}`, normalized-JSON accept.

### Decisive source
```python
# track :1480–1491
        payload = {"eventBody": eventBody, "eventInfo": eventInfo}
        res = self._post(
            "/li/track",
            base_request=True,
            headers={
                "accept": "*/*",
                "content-type": "text/plain;charset=UTF-8",
            },
            data=json.dumps(payload),
        )

        return res.status_code != 200
```

**Flow (track):** wrap → stringify → `_post(..., base_request=True)` flips host to `https://www.linkedin.com` BEFORE joining `/li/track` → inverted bool from status 200. **Flow (unfollow):** namespace the entity id into a `fs_followingInfo` URN → POST the action-verb URI on the API plane → `err = res.status_code != 200`.
**Invariant:** both planes return the suite-standard INVERTED error bool (`True` = error). The host switch MECHANISM itself is owned by voyager-api-client; this capsule pins its only non-auth CONSUMER: `base_request=True` appears exactly once in endpoint code (:1483). Action verbs ride the query string while the resource path stays a plural noun; telemetry deliberately does NOT claim application/json.
**Probe:** no upstream tests exist — source-grounded grep at HEAD: `base_request=True` ⇒ :1483 only; `text/plain` ⇒ :1486; `fs_followingInfo` ⇒ :1566; `unfollowByEntityUrn` ⇒ :1568; inverted bool returns ⇒ :1491 and :1573–75.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "open-linkedin-api", query: "track unfollow entity base_request telemetry", limit: 10, fields: ["signature", "lines"] });
// resolves Linkedin.unfollow_entity :1557–1577 and Linkedin.track :1479–1491 (observed this pass)
```

## Verdict
Adopt the two-plane split: analytics/beacon traffic goes to the bare host under text/plain with accept */*, while state mutations stay on the API plane using noun-path + ?action= verb grammar with URN-namespaced payloads. Adapt the payload schema (eventBody/eventInfo are vendor shapes). Omit nothing structural — but do not generalize `base_request=True`: it exists for auth HTML pages and this one beacon, not as a general escape hatch. Cross-ref: mutation body family in voyager-mutation-endpoints (add_connection/send_message/follow_company share the inverted-bool convention). Coverage caveat: no upstream tests; coverage check on linkedin.py = no_recorded_issue + metadata_match.
