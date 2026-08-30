---
name: jobspy-foundation
description: "Use when scraping job listings across sites (LinkedIn, Indeed, Glassdoor, ZipRecruiter, Google, Naukri, Bayt, BDJobs): a unified Scraper abstraction, proxy rotation, salary/number parsing, and per-site adapter patterns."
disable-model-invocation: true
---
# JobSpy Foundation

## Use this for
Scrape job listings across many sites behind one typed abstraction: a shared `Scraper` contract, a multi-site orchestrator that flattens into a normalized DataFrame, proxy rotation and session factories, salary/number parsing, and per-site adapter patterns. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval. **No in-repo test suite exists** — every capsule is verified against source; treat the graph as a discovery index, not truth.

## Load the matching source dump
- `references/orchestrator-flatten.md` — how `scrape_jobs` flattens N per-site results into one sorted, column-stable DataFrame.
- `references/orchestrator-failure-contract.md` — SCRAPER_MAPPING registry + unshielded futures: why partial success is an adapter-side obligation.
- `references/contract.md` — the typed contract: ScraperInput, Scraper ABC, JobPost union schema, Country/JobType routing tables.
- `references/employment-type-mappers.md` — JobType alias-tuple lookups: first-vs-last-match divergence, raise-vs-None misses, dead Glassdoor twin.
- `references/sessions-proxies.md` — RotatingProxySession, the two asymmetric session flavors, create_session factory.
- `references/logging-verbosity-plane.md` — import-before-tune verbose retune of eight JobSpy:* loggers; display-name fixups.
- `references/salary-parsing.md` — threshold-based salary extraction, locale-safe currency parsing, annualization.
- `references/contact-email-harvest.md` — extract_emails_from_text regex plus the six-adapter wiring matrix and flatten join guard.
- `references/scraper-pattern.md` — the per-site adapter pattern with guest endpoints, pagination ceilings, partial-success.
- `references/remote-detection.md` — keyword OR-ing across title/description/location, per-site variants.
- `references/date-normalization-ladders.md` — per-board recency inputs (ageInDays, format ladders, relative labels, ms epochs) normalized degrade-to-None.
- `references/indeed-graphql-driver.md` — Indeed's GraphQL cursor pagination, composite filters, employer-dossier enrichment.
- `references/indeed-compensation-mapper.md` — Indeed structured compensation: baseSalary-vs-estimated split provenance, strict interval raise, int() truncation.
- `references/glassdoor-adapter.md` — Glassdoor's CSRF bootstrap, location resolution, threaded description fetch.
- `references/ziprecruiter-adapter.md` — ZipRecruiter's mobile-app API, session-event bootstrap, continue-token pagination.
- `references/google-adapter.md` — Google's SERP async-cursor pagination and brittle nested-JSON extraction.
- `references/naukri-adapter.md` — Naukri's placeholder-driven location/salary parsing and Indian Lakh/Crore conversion.
- `references/linkedin-guest-pagination.md` — LinkedIn's guest-endpoint cursor ladder, 1000-ceiling, partial-success error policy.
- `references/linkedin-card-parsing.md` — LinkedIn search-card → JobPost: salary span, degrade-to-default selectors, datetime fallback (#343).
- `references/linkedin-details-enrichment.md` — LinkedIn details-page enrichment: signup guard, criteria tables, applyUrl extraction.
- `references/linkedin-util-plane.md` — LinkedIn job-type/level/industry utils: F/P/I/C/T codes, enum-membership traps, live crash edge.
- `references/html-scrapers-bdjobs-bayt.md` — BDJobs/Bayt selector-fallback ladders and responsibilities-section extraction.
- `references/description-conversion.md` — markdown/plain/HTML converters and the remove-attributes prettify pattern.

## Capsule map
- **Orchestration** — `orchestrator-flatten`: concurrent per-site scrape, dedupe, all-NA column drop, `desired_order` backfill, `(site, date_posted)` sort.
- **Orchestration** — `orchestrator-failure-contract`: no try/except between future.result() and scraper.scrape(); adapters own partial success; registry totality.
- **Typed contract** — `contract`: ScraperInput → Scraper(ABC) → JobResponse; Country/JobType as routing tables; one-union JobPost.
- **Typed contract** — `employment-type-mappers`: i18n alias-tuple membership; user-path raises, shared normalizer last-match-wins, site twins first-match lists; hyphenated labels miss.
- **Sessions & proxies** — `sessions-proxies`: rotation via `itertools.cycle` + `http://localhost` no-proxy sentinel; retry only on the requests flavor.
- **Logging** — `logging-verbosity-plane`: JobSpy:{Name} namespaces born at import; set_logger_level retunes post-import; fixups reuse logger identity; docstring/default contradiction.
- **Salary & numbers** — `salary-parsing`: refuse-to-guess interval inference; locale-safe currency; annualization.
- **Contact harvest** — `contact-email-harvest`: strict email regex, None-vs-[] shape, guarded/unguarded/dead-import wiring matrix, [] -> None join guard.
- **Per-site pattern** — `scraper-pattern`: guest endpoints, hard pagination ceiling, cross-page dedupe, partial-success.
- **Remote detection** — `remote-detection`: keyword OR over title/description/location, per-site keyword sets.
- **Dates** — `date-normalization-ladders`: ageInDays arithmetic, five-format strptime ladder, relative-label-then-ms-epoch; all degrade to None on naive local clocks.
- **Indeed** — `indeed-graphql-driver`: GraphQL cursor pagination, composite filters, employer-dossier enrichment.
- **Indeed** — `indeed-compensation-mapper`: amounts prefer baseSalary, currency prefers estimated.currencyCode; unknown unitOfWork raises; int() truncates.
- **Glassdoor** — `glassdoor-adapter`: CSRF bootstrap, location→id/type, threaded per-job description fetch.
- **ZipRecruiter** — `ziprecruiter-adapter`: session-event bootstrap, continue-token pagination, job-page enrichment.
- **Google** — `google-adapter`: async forward-cursor pagination, magic-key nested-JSON extraction (brittle).
- **Naukri** — `naukri-adapter`: typed-placeholder parsing, Indian salary-unit conversion, work-from-home inference.
- **LinkedIn** — `linkedin-guest-pagination`: guest cursor ladder, hard 1000-ceiling, page-level partial success vs card-level raise.
- **LinkedIn** — `linkedin-card-parsing`: degrade-don't-fail card contract, `listdate--new` datetime fallback (#343), arity-ladder location.
- **LinkedIn** — `linkedin-details-enrichment`: empty-dict degradation, post-redirect signup guard, strip-before-serialize, applyUrl regex contract.
- **LinkedIn** — `linkedin-util-plane`: single-letter f_JT codes, last-match-wins enum lookup vs raising twin, `[None]`/`.lower()` executed edges.
- **HTML scrapers** — `html-scrapers-bdjobs-bayt`: selector-fallback ladders, responsibilities-section extraction, stop-on-no-new-jobs.
- **Description conversion** — `description-conversion`: markdown/plain converters; remove-attributes-before-prettify.

## Extending the foundation
Add one `references/<seam>.md` capsule for one graph-selected, source-confirmed porting question. Add one matching loader line and map entry; keep evidence in the capsule, not this leaf. For a new site, copy the per-site package shape (`__init__.py` + `constant.py` + `util.py`) from `scraper-pattern.md`.

## Provenance
JobSpy (MIT), `main@fda080a` (2026-02-18); Codebase Memory project `JobSpy` (301 nodes / 1301 edges, index_mode full, only `.git` excluded). No in-repo test suite — all claims verified against source; the graph is a discovery index, not truth. Pass 2 (2026-08-24, drain-lane-sweep-rover) added the four-capsule LinkedIn plane at the SAME pin (zero drift): symbol-granular citation census exposed `linkedin/__init__.py`+`linkedin/util.py` as never-mined; two executed edges recorded (`[None]` job_type ValidationError; live `.lower()` crash when a details page lacks Seniority level). Pass 3 (2026-08-24, miner-JobSpy deep-learning lane) added six capsules at the SAME pin (zero drift): indeed-compensation-mapper, employment-type-mappers (incl. zero-caller Glassdoor twin), orchestrator-failure-contract (unshielded futures), contact-email-harvest (bdjobs dead import), logging-verbosity-plane (import-before-tune), date-normalization-ladders; probes executed byte-for-byte against standalone-loaded jobspy/model.py (pydantic OK); package probes blocked on pandas/markdownify/tls_client absence; work record created at JobSpy-work/.

## Full view (memory graph)
Revalidate `JobSpy` before porting: run `index_status`, `check_index_coverage`, `search_graph`, `trace_path`, and `get_code_snippet`. Record the graph root, branch, commit, mode, node/edge counts, freshness, and any coverage caveats; source and direct tests decide shipped claims. `scrape_jobs` outbound trace confirms the flatten path (13 callees: Country.from_string, Location, ScraperInput, convert_to_annual, extract_salary, get_enum_from_value, set_logger_level); `create_session` inbound trace confirms the 8 site callers.

## Boundaries
Adopt the typed scraper contract, session factories, salary/number parsing, and per-site adapter patterns; adapt site selectors, auth, retry budgets, and country routing; omit a board's proprietary flows, monetization, and the brittle Google positional-index parsing unless a target requires them.
