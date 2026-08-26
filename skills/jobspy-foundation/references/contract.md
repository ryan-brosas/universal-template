<!-- capsule-v2 -->
# Typed contract — ScraperInput → Scraper(ABC) → JobResponse/JobPost, and Country/JobType as routing tables

**Source:** JobSpy MIT `main@fda080a`; Codebase Memory `JobSpy`. **Question:** What is the shared typed contract every site scraper implements, and why are `Country`/`JobType` enums structured as tuples of aliases + per-site routing codes?

## The chain
**Path/Symbol:** `jobspy/model.py` — `ScraperInput` (303–322), `Scraper` (325–335), `JobPost` (239–281), `JobResponse` (283–284), `Country` (60–178), `JobType` (10–57), `Compensation` (227–231), `Location` (181–205), `SalarySource` (298–300), `DescriptionFormat` (234–237), `CompensationInterval` (208–224), `Site` (287–295).
**Signature:** `Scraper.__init__(self, site, proxies=None, ca_cert=None, user_agent=None)` + `@abstractmethod scrape(self, scraper_input: ScraperInput) -> JobResponse`. `JobResponse.jobs: list[JobPost]`.
**Data Shape:** `ScraperInput` defaults — `country=Country.USA`, `distance=None`, `is_remote=False`, `offset=0`, `description_format=DescriptionFormat.MARKDOWN`, `request_timeout=60`, `results_wanted=15`, `hours_old=None`. `JobPost` is ONE union schema: common fields + commented per-site extensions (LinkedIn `job_level`/`job_function`; Indeed `company_*`/`banner_photo_url`; Naukri `skills`/`experience_range`/`company_rating`/`company_reviews_count`/`vacancy_count`/`work_from_home_type`).

### Decisive source
```python
class Country(Enum):
    UK = ("uk,united kingdom", "uk:gb", "co.uk")          # (name_aliases, indeed_sub:api_code, glassdoor_sub:tld)
    USA = ("usa,us,united states", "www:us", "com")
    US_CANADA = ("usa/ca", "www")                          # internal: ziprecruiter
    WORLDWIDE = ("worldwide", "www")                       # internal: linkedin
    @property
    def indeed_domain_value(self):
        subdomain, _, api = self.value[1].partition(":")
        return (subdomain, api.upper()) if subdomain and api else (self.value[1], self.value[1].upper())
    @classmethod
    def from_string(cls, s):
        s = s.strip().lower()
        for c in cls:
            if s in c.value[0].split(","):
                return c
        raise ValueError(...)

class JobType(Enum):
    FULL_TIME = ("fulltime", "períodointegral", "estágio/trainee", "cunormăîntreagă", "tiempocompleto", "vollzeit", "voltijds", "tempointegral", "全职", "plnýúvazek", "fuldtid", "دوامكامل", ...)  # 25+ localized aliases
```

**Flow:** `scrape_jobs` builds one `ScraperInput` → dispatches per site to a `Scraper` subclass → each returns a `JobResponse`. `Country`/`JobType` are enums whose VALUES are tuples: `Country` packs `(comma-split name aliases, "indeed_sub:api_code", "glassdoor_sub:tld")`; `JobType` packs dozens of localized job-type aliases so substring matching works in any locale.
**Invariant:** `Country` is a ROUTING table, not a list — `indeed_domain_value`/`glassdoor_domain_value` unpack the `:` into subdomain + code/TLD; aliases split on commas; the two INTERNAL members `US_CANADA`/`WORLDWIDE` never render in output (`Location.display_location()` special-cases both out). `JobType` string matching is a simple substring check against the alias tuple (`get_enum_from_job_type`). `Location.display_location()` composes city/state/country, takes the first alias before a comma, uppercases `usa`/`uk`, title-cases the rest.
**Probe:** no in-repo test suite; the contract is consumed by every site subclass (`jobspy/linkedin/__init__.py`, `jobspy/naukri/__init__.py`, `jobspy/bdjobs/__init__.py`) as a typed `JobResponse`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "JobSpy", query: "ScraperInput Scraper JobPost Country JobType enum", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the enums-as-routing-tables pattern (tuples carrying per-site domains + localized aliases in the enum value, internal pseudo-members with explicit display suppression) and the one-union `JobPost` schema with site-prefixed ids (`li-`, `in-`, `gd-`, `zr-`, `go-`, `nk-`, `bayt-`, `bdjobs-`). Adapt the alias lists to your locales. Omit `Country`'s per-site domain routing if you scrape a single site. Coverage caveat: no in-repo tests; verified against source + all site subclasses.
