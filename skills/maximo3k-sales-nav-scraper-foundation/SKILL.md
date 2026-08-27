---
name: maximo3k-sales-nav-scraper-foundation
description: "Use when scraping LinkedIn Sales Navigator saved-search result pages into CSV with Selenium: driver bootstrap, unvalidated three-key config.json contract, print-only telemetry that leads the CSV ledger, manual-captcha login handoff, pagination loop, stale-safe scroll+extract with data-anonymize selectors, index-coupling and stale-wait failure modes, wait-then-sleep settle timing, header-on-first-write CSV append, tiered failure containment (card-degrade / page-abort / setup-crash), page-batched crash-bounded CSV durability, parent-anchor profile-URL extraction, and the unprotected mid-run authwall crash boundary, the manifest-less import-only dependency surface, the no-main-guard import-side-effect entrypoint with best-effort teardown, and row-projection partiality (an exception persists the flushed page prefix while process death loses it)."
disable-model-invocation: true
---
# maximo3k-sales-nav-scraper: LinkedIn Sales Navigator CSV Scraper Foundation

## Use this for
Scrape a LinkedIn Sales Navigator saved-search people list into a CSV using Selenium: create one clean logged-out Chrome session via webdriver-manager, log in through a possible security check by fixed-window human handoff, page through results with the "Next" pagination button, scroll each result card into view and extract name/title/company/location/link via `data-anonymize` selectors (re-locating each card by index against stale elements), and append rows to a CSV with a header written only on first write. Source is ground truth; there are no direct tests in the repo, so each capsule states that coverage caveat.

## Load the matching source dump
### Setup and telemetry
- `references/config-contract-unvalidated-load.md` — the unvalidated three-key `config.json` load at module scope: missing keys crash tier C inside `login_to_site`, placeholders pass every structural check, README excludes lead-list URLs.
- `references/manifestless-dependency-contract.md` — twelve import lines are the only dependency declaration: no manifest exists anywhere in the tree, `Options` (:5) is dead, webdriver-manager fetches the chromedriver binary over the network at :20.
- `references/console-telemetry-leads-ledger.md` — nine bare `print` sites are the only progress channel; stdout leads the CSV by up to one page and carries raw profile URLs/names (:82/:98).
### Session and auth
- `references/driver-bootstrap.md` — one module-level Chrome session via webdriver-manager, deliberately profile-less so every run starts logged out.
- `references/login-flow.md` — credential-fill → RETURN → fixed 15 s security-check window → explicit navigation to the saved-search start URL.
### Extraction loop
- `references/extraction.md` — per-card NA-defaulted extraction of the five `data-anonymize` fields inside `li.artdeco-list__item.pl3.pv3`, with dual success/except append sites so a bad card yields an all-NA row, never a partial one.
- `references/parent-anchor-link.md` — the profile URL has no `data-anonymize` tag: it is the `href` of the name span's PARENT anchor (`By.XPATH, ".."` structural hop).
- `references/stale-refind.md` — re-locate each card by enumerate index with the caller's exact selector before touching its fields.
- `references/stale-wait-boundary.md` — the :72 visibility wait itself raises `StaleElementReferenceException` through `until()` before the :74 heal; staleness is CONTAINED to one NA row, not prevented.
- `references/index-coupling-failure-modes.md` — two independent `find_elements` calls bound by position: shrink ⇒ IndexError row, order shift ⇒ silent wrong-card data, stale original ⇒ NA row — all one-row costs inside the card-tier try.
- `references/page-settle-timing.md` — four fixed-sleep sites layered on explicit waits: presence ≠ ready (15/10/4/1 s ladder).
### Output and pagination
- `references/csv-output.md` — append-mode CSV with the header written only when `file.tell() == 0`.
- `references/mid-run-authwall-death.md` — the :129 page-level `.artdeco-list` wait sits outside every try tier: a mid-run authwall crashes the run and skips `driver.quit()` (window left open).
- `references/csv-ledger-durability.md` — the commit unit is the PAGE (one bulk append per `scroll_extract` call): a crash loses exactly the current page; the ledger is append-only with no dedup.
- `references/csv-row-projection-partiality.md` — rows are written by direct five-key indexing over a closed producer schema; an exception persists the flushed prefix rows while process death loses the whole buffered page.
- `references/pagination.md` — while-loop pages on the enabled "Next" button; disabled, absent, or erroring all terminate.
### Failure containment
- `references/failure-topology.md` — two nested catch tiers (card → all-NA row + continue; page navigation → break) and NO handler above them (login/config load crash the run).
- `references/module-entry-no-main-guard.md` — flat top-level program with no `__main__` guard: importing launches Chrome and runs the entire scrape; `driver.quit()` (:164) is a best-effort last statement with no `finally` anywhere.

## Capsule map
- **Config contract** — `config-contract-unvalidated-load`: an unvalidated three-key `config.json` load whose missing keys crash tier C.
- **Console telemetry leads the ledger** — `console-telemetry-leads-ledger`: nine print sites are the ONLY progress channel, and stdout carries PII.
- **CSV ledger durability** — `csv-ledger-durability`: one write call per page, append-only, no dedup: crash loses exactly the current page.
- **CSV output** — `csv-output`: append five-field rows and write the header only on first write.
- **Row-projection partiality** — `csv-row-projection-partiality`: direct five-key indexing makes schema violations latent tier-C crashes, and an exception persists the page prefix while process death loses it.
- **Driver bootstrap** — `driver-bootstrap`: one Chrome session via webdriver-manager with no profile reuse.
- **Extraction** — `extraction`: scroll each card into view and pull the five data-anonymize fields with NA defaults.
- **Failure topology** — `failure-topology`: card errors degrade to NA rows, pagination errors end the run, login errors crash it.
- **Index-coupling** — `index-coupling-failure-modes`: two independent `find_elements` calls over one mutable list: the failure modes of matching by position.
- **Login flow** — `login-flow`: authenticate through a possible captcha and land on the saved-search URL.
- **Manifest-less dependency contract** — `manifestless-dependency-contract`: the import block is the ONLY dependency declaration.
- **Mid-run authwall death** — `mid-run-authwall-death`: the page-level presence wait sits OUTSIDE every try tier.
- **No-main-guard entrypoint** — `module-entry-no-main-guard`: importing the module launches Chrome and runs the whole scrape; quit() is best-effort.
- **Page-settle ladder** — `page-settle-timing`: explicit sleeps stacked on top of every explicit wait.
- **Pagination** — `pagination`: page through Sales Navigator results on the enabled Next button.
- **Parent-anchor link extraction** — `parent-anchor-link`: the profile URL lives on the PARENT of the name span, not the span itself.
- **Stale-element re-find** — `stale-refind`: re-locate each card by index before touching its fields.
- **Stale-wait boundary** — `stale-wait-boundary`: the visibility wait itself raises StaleElementReferenceException before the re-find can heal.
## Extending the foundation
Add one graph-selected, source-confirmed capsule per new porting seam (e.g. a challenge-classification seam or a different result-card layout). Add exactly one loader line under the matching subsystem group and one map row; retain decisive source, an invariant, a direct-test probe (or an explicit no-test caveat), and a live-verified `search_graph` retrieval in the capsule rather than expanding this leaf.

## Provenance
maximo3k-sales-nav-scraper (license file, `main@bdcd2e5197929f78631ab127d2fd10cee18807ca`; canonical root `/mnt/hdd/utopia/inspo/linkedin/maximo3k-sales-nav-scraper`, symlink twin without the segment); Codebase Memory project `maximo3k-sales-nav-scraper` (FULL mode, ready, 30 nodes / 42 edges, generation 2026-08-18T02:08Z, head==base==pin — zero drift verified 2026-08-23 pass 2). Pass 2 (2026-08-23): whole-file source re-read of the 163-line production script; 4 new capsule-v2 (bootstrap/login/settle/stale-refind) adopted from an interrupted sibling draft after line-by-line verification; pass-1 extraction/pagination corrected against source (local-not-module `results`, dual append sites, unreachable per-field fallbacks, line ranges). The graph indexes only the 4 function symbols (module-level statements have no symbols) — Retrieve blocks cite symbol-resolving queries. No test files exist in the repo — all claims are source-grounded only; the CSV header guard additionally carries an executed stdlib behavioral probe (GREEN×2 + RED control). Pass 3 (2026-08-24, deepening-A lane): symbol-granular gap sweep at unchanged pin `bdcd2e5` exposed the last uncited seams — +3 capsule-v2 (`failure-topology`, `csv-ledger-durability`, `parent-anchor-link`), 7→10 refs; all three Retrieve queries live-executed before writing (zero-miss). Pass 4 (2026-08-24, deepening-B lane): whole-repo census re-read at the same zero-drift pin `bdcd2e5` (graph ready, head==base==pin, parse_partial 0) + all-10-capsule dedup adjudication found five unowned porting questions — +5 capsule-v2 (`config-contract-unvalidated-load`, `console-telemetry-leads-ledger`, `index-coupling-failure-modes`, `mid-run-authwall-death`, `stale-wait-boundary`), 10→15 refs; every deterministic probe executed byte-exact BEFORE writing (T1–T19 incl. two expectation corrections: print census = exactly 9 sites with :32 preceding the :120 write call site, and find_elements census = exactly 2 sites); every Retrieve query live-resolved against project `maximo3k-sales-nav-scraper` before writing (hyphenated-selector queries return total:0 on this tiny BM25 graph — capsules carry symbol-anchored alternates). Pass 5 (2026-08-25, FAC-72 deepening-C lane): whole-file internalization re-read at unchanged zero-drift pin `bdcd2e5` (graph ready, head==base==pin, FULL 30 nodes / 42 edges, parse_partial 0) adjudicated every candidate seam against all 15 capsules — +3 capsule-v2 (`manifestless-dependency-contract`, `module-entry-no-main-guard`, `csv-row-projection-partiality`), 15→18 refs; license identified GPL-3.0; git history depth 1 (single squashed commit — the pin IS genesis); three phantom builtin Method nodes (`list.pop`/`str.lower`/`str.upper`) have NO HEAD call sites and are recorded as never-cite coverage caveats; Retrieves R1–R3 live zero-miss pre-write (the Module node itself is not name_pattern-retrievable — module statements carry no symbols) and Probes P1–P3 executed byte-exact BEFORE writing, including a stdlib behavioral probe confirming close-on-exception prefix persistence (header+2 data rows survived a simulated mid-page raise).

## Full view (memory graph)
Revalidate `maximo3k-sales-nav-scraper` before porting: run `index_status`, `check_index_coverage`, `search_graph`, `trace_path`, and `get_code_snippet`. Record the graph root, branch, commit, mode, node/edge counts, freshness, and any coverage caveats; source decides shipped claims. The single production file `prospect_scraper_sales_navigator.py` reports `no_recorded_issue` + `metadata_match` (best-effort signal); only `.git` is excluded by design.

## Boundaries
Adopt the pagination loop, the stale-safe scroll+extract contract, the wait-then-sleep settle ladder, the profile-less single-session bootstrap, the manual-challenge login handoff, and the header-on-first-write CSV append. Adapt the CSS selectors, the four timer values (author-tuned ratios, not constants), and field names to the host and current LinkedIn DOM. Omit automated challenge solving (deliberately human-handed), the hard-coded `prospects_1.csv` path, and the module-level import-time side-effect structure unless porting the script wholesale.
