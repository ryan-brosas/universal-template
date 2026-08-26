<!-- capsule-v2 -->
# Voyager GraphQL query-id profile components — how do I fetch a LinkedIn profile section via the GraphQL queryId endpoint and normalize the grouped-component response?

**Source:** open-linkedin-api MIT `main@5feee360ec26719d07d5e67638045e751b48a74c` (`linkedin.py`). Codebase Memory `open-linkedin-api`. **Question:** what is the `/graphql?variables=(...)&queryId=...` request shape for profile components, and how do I parse both flat and grouped (multi-position) experience items from the same response?

## GraphQL queryId fetch + grouped-item parse
**Path/Symbol:** `linkedin.py:Linkedin.get_profile_experiences` (:865–1011), `get_profile_contact_info` (:658–701), `get_profile_skills` (:702–727), `get_profile` (:728–851). **Signature:** `get_profile_experiences(urn_id) -> List`; builds `variables=(profileUrn:<quoted>,sectionType:experience)` and a fixed `queryId`.
**Data Shape:** the response nests `components.entityComponent` with `titleV2.text.text` (title), `subtitle.text` (`"Company · EmploymentType"`), and `metadata`; grouped items (one company, many positions) have a different structure handled by `is_group_item`.

### Decisive source
```python
profile_urn = f"urn:li:fsd_profile:{urn_id}"
variables = ",".join([f"profileUrn:{quote(profile_urn)}", "sectionType:experience"])
query_id = "voyagerIdentityDashProfileComponents.7af5d6f176f11583b382e37e5639e69e"
res = self._fetch(f"/graphql?variables=({variables})&queryId={query_id}&includeWebMetadata=true",
                  headers={"accept": "application/vnd.linkedin.normalized+json+2.1"})

def parse_item(item, is_group_item=False):     # grouped items have different structure
    component = item["components"]["entityComponent"]
    title = component["titleV2"]["text"]["text"]
    subtitle = component["subtitle"]
    company = subtitle["text"].split(" · ")[0] if subtitle else None
    employment_type = subtitle["text"].split(" · ")[1] if subtitle and len(...) > 1 else None
    metadata = component.get("metadata", {}) or {}
```

**Flow:** build the `variables=(...)` tuple with the quoted `profileUrn` and `sectionType`, append the fixed `queryId` and `includeWebMetadata=true`, GET via `_fetch` with the normalized JSON accept header → walk `elements`, and for each call `parse_item` with the grouped flag when the item represents multiple positions → extract title from `titleV2.text.text`, company/employment-type by splitting `subtitle.text` on `" · "`, and pull the rest from `metadata`.
**Invariant:** the GraphQL response nests text under `titleV2.text.text` (not a flat `title` field) and splits company/employment-type from one `subtitle.text` string on `" · "` — a porter must know both or the parse silently yields `None`. Grouped experience items (company with several roles) need the `is_group_item` branch because their component structure differs from flat items. The `queryId` is a stable-but-rotating opaque string that must be re-captured from a live network trace when it expires.
**Probe:** no upstream tests — coverage caveat recorded. Graph anchors resolve: `get_profile_experiences`, `get_profile`, `get_profile_contact_info`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "open-linkedin-api", query: "get_profile_experiences", limit: 5 });
await mcp.codebase_memory.search_graph({ project: "open-linkedin-api", query: "get_profile_contact_info", limit: 5 });
```

## Verdict
Adopt the `/graphql?variables=(...)&queryId=...` request shape, the `titleV2.text.text`/`subtitle.text` parse, and the grouped-item branch; adapt the queryId (rotates) and the `sectionType` values; omit the hard-coded decorationId/queryId strings from production code. Caveat: source-grounded only, no test coverage.
