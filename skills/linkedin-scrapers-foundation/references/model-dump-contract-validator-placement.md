<!-- capsule-v2 -->
# Model dump contract + validator placement — where does URL validation belong across a pydantic model family whose entities differ in identity type?

**Source:** joeyism-linkedin-scraper GPL-3 `master@b1cdc1c0e85b…`; Codebase Memory `joeyism-linkedin-scraper`. **Question:** which models get a canonical-URL validator, which stay validator-free, and how do to_dict/to_json stay thin?

## Validate canonical-URL identities at construction; URN-keyed models stay open
**Path/Symbol:** `linkedin_scraper/models/job.py:Job.validate_linkedin_url` (:17–23) + `to_dict/to_json` (:31–48); `models/company.py:Company.validate_linkedin_url` (:44–50); `models/post.py:Post` (:5–15, NO validator); declared-but-unfilled `Company.employees/showcase_pages/affiliated_companies` (:41–43).
**Signature:** `@field_validator('linkedin_url') @classmethod def validate_linkedin_url(cls, v: str) -> str`; `def to_dict(self) -> Dict[str, Any]: return self.model_dump()`; `def to_json(self, **kwargs) -> str: return self.model_dump_json(**kwargs)`.
**Data Shape:** Job/Company: one required `linkedin_url: str` + everything else Optional with None defaults; list fields use `Field(default_factory=list)`. Post: ALL fields Optional including linkedin_url and urn. Dump output is schema-total (every declared field present, Nones included).

### Decisive source
```python
class Job(BaseModel):
    linkedin_url: str
    job_title: Optional[str] = None      # optional-everything EXCEPT identity
    ...
    @field_validator('linkedin_url')
    @classmethod
    def validate_linkedin_url(cls, v: str) -> str:
        if 'linkedin.com/jobs' not in v:
            raise ValueError('Must be a valid LinkedIn job URL (contains /jobs)')
        return v

class Post(BaseModel):                    # URN-keyed entity: NO url gate at all
    linkedin_url: Optional[str] = None
    urn: Optional[str] = None
    image_urls: List[str] = Field(default_factory=list)
```

**Flow:** scraper harvests Optional DOM values → constructs the model ONCE at the end of scrape() → pydantic enforces identity (bad URL ⇒ ValidationError before any consumer sees the object) → consumers read via to_dict()/to_json() delegates over model_dump/model_dump_json.
**Invariant:** validator presence tracks IDENTITY TYPE, not convention — URL-identified entities (Job '/jobs', Company '/company/') gate their canonical URL so garbage fails fast; URN-identified Post stays validator-free because its stable key is the URN. Dumps are total: absent DOM still emits the field as None/[]. Declared-but-unfilled fields (Company employees lists) are schema-ahead-of-scraper enrichment slots — legal because dumps stay total.
**Probe (executed):** `python3 -c "from linkedin_scraper.models.job import Job; Job(linkedin_url='https://example.com/x')"` → **ValidationError raised**; `Post(linkedin_url='https://anything.example')` → **accepted**; `Job(linkedin_url='https://linkedin.com/jobs/view/123').to_dict()` → includes `benefits: None`. Repo's own units green: `pytest -m unit` → test_job_model_to_dict/to_json + test_company_model_to_dict/to_json + person twins all pass (7 passed / 15 deselected).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "joeyism-linkedin-scraper", query: "Job Post Company model validators pydantic", limit: 6 });
// → tests.test_job_scraper.test_job_model_to_dict/:56–70, test_company_model_to_dict/:49–64 (+TESTS edges)
await mcp.codebase_memory.get_code_snippet({ project: "joeyism-linkedin-scraper", qualified_name: "joeyism-linkedin-scraper.linkedin_scraper.models.job.Job" });
```

## Verdict
Adopt the placement rule (validate only the identity field; keep every other field Optional-with-total-dumps) and the two-line dump delegates. Adapt substring gates per entity type. Omit nothing structural — but do NOT copy this onto Person blindly: profile-schema already covers Person's canonical-/in/-slug normalization ladder; here the porting question is WHERE validation sits across the family. Evidence: runnable units + direct ValidationError probe at pinned HEAD.
