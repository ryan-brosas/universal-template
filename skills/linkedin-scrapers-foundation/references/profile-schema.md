<!-- capsule-v2 -->
# Profile schema & ID extraction — how do I normalize LinkedIn identities (URNs, member IDs, profile URLs) across sources?

**Source:** joeyism-linkedin-scraper GPL-3 `master@b1cdc1c0e85bee8764d62565d229c682e5eb81bb` (`models/person.py`); open-linkedin-api MIT `main@5feee360` (`utils/helpers.py` URN parsers); linvo-scraper MIT (`pagesTask` mapping :100–115). Codebase Memory projects of the same names. **Question:** what is the canonical minimal profile shape, and how do the three ID encodings map to a canonical `/in/<slug>` URL?

## Person pydantic model + URN→URL extraction
**Path/Symbol:** `linkedin_scraper/models/person.py:Person` (:53–133, validator :71–77); `open_linkedin_api/utils/helpers.py:get_id_from_urn` (:6–12), `get_urn_from_raw_update` (:15–22); linvo entityUrn split (`linkedin.sales.page.service.ts` :103–106).
**Signature:** `Person(linkedin_url: str, name, location, about, open_to_work=False, experiences[], educations[], interests[], accomplishments[], contacts[])`; `get_id_from_urn("urn:li:fs_miniProfile:<id>") -> <id>` (split(":")[3]); `get_urn_from_raw_update(raw) -> raw.split("(")[1].split(",")[0]`.
**Data Shape:** three encodings for one identity — (a) Voyager URN `urn:li:fs_miniProfile:ABC123`, (b) parenthesized composite `urn:li:fs_salesProfile:(ABC123,NAME,title)`, (c) DOM attributes `data-scroll-into-view="fs_salesProfile:(…)"` / `data-job-id`.

### Decisive source
```python
@field_validator("linkedin_url")
def validate_linkedin_url(cls, v):
    if "linkedin.com/in/" not in v:
        raise ValueError("Must be a valid LinkedIn profile URL (contains /in/)")
    return v

@property
def company(self):      # most-recent-first list convention
    return self.experiences[0].institution_name if self.experiences else None
```
```ts
// linvo: parenthesized URN → public URL (same move hassan does on the DOM attribute)
link: "https://www.linkedin.com/in/" + e.entityUrn.split("(")[1].split(",")[0].trim()
// keep only real people rows:
elements.filter(f => f.firstName && f.entityUrn.indexOf("fs_salesProfile") > -1)
```

**Flow:** scrape/API returns raw rows → filter to person-typed entries (firstName present AND urn namespaced fs_salesProfile/fs_miniProfile) → split parenthesized or colon URN → first segment = public member slug → build `/in/<slug>/` → validate with the `/in/` substring check before persisting.
**Invariant:** every field is Optional except the validated `linkedin_url` — partial profiles are legal, invalid IDs are not; "most recent" is positional (index 0), never date-computed. The same split logic works on JSON payloads (linvo), HTML `<code>` islands (linvo fallback), and DOM attributes (hassan :184–186).
**Probe:** `tests/test_person_scraper.py::test_person_model_to_dict/:test_person_model_to_json` (:84+) pin model round-trip; scraper fetch tests are integration-gated behind a session fixture (skip without `linkedin_session.json`). open-linkedin-api has no tests — caveat recorded.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "joeyism-linkedin-scraper", query: "Person", limit: 5 });
await mcp.codebase_memory.search_graph({ project: "open-linkedin-api", query: "get_id_from_urn", limit: 5 });
```

## Verdict
Adopt optional-everything-but-validated-URL models and the three-way URN→slug normalization; adapt model fields and namespaces to host; omit linvo's image-URL artifact assembly unless porting avatars too. Probe caveat: only the model layer is unit-tested; extraction is source-grounded.
